"""Builds results/summary.csv (accuracy, failures, latency, cost) from results/per_item.csv.

Usage:
    python src/cost.py --in results/per_item.csv --out results/summary.csv

Accuracy is reported on the frozen *test* split only (n/50). Latency and token
counts use every real call (dev + test) since they don't depend on the label.

Cost per 1k requests
    API models   : mean input/output tokens from the `usage` field x list price.
    Local model  : (hardware $/h + power $/h) / requests per hour, plus ops time
                   spread over today's traffic.
It also writes results/cost_model.json with the 100x projection and the
break-even volume, which the report and the web app read.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

FAILURES = ["wrong_result", "sql_error", "parse_error", "refusal", "timeout", "api_error", "truncated"]


def percentile(values, p):
    """Nearest-rank percentile (no interpolation): the smallest value with >= p% of data at or below it."""
    if not values:
        return None
    s = sorted(values)
    k = max(1, math.ceil(p / 100 * len(s)))
    return s[k - 1]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def local_costs(mean_latency_ms, requests_per_month):
    sh = config.SELF_HOST
    hw_per_h = sh["hardware_price_usd"] / sh["hardware_life_hours"]
    power_per_h = sh["power_kw"] * sh["electricity_usd_per_kwh"]
    req_per_h = 3_600_000 / mean_latency_ms  # one request at a time, as measured
    compute_per_req = (hw_per_h + power_per_h) / req_per_h
    ops_month = sh["ops_hours_per_month"] * sh["engineer_usd_per_hour"]
    capacity_month = req_per_h * sh["dedicated_hours_per_month"]
    # Dedicated always-on box: hardware written off over 36 months + 24/7 power.
    box_month = sh["hardware_price_usd"] / 36 + power_per_h * sh["dedicated_hours_per_month"]
    machines = max(1, math.ceil(requests_per_month / capacity_month))
    return {
        "hw_usd_per_hour": hw_per_h + power_per_h,
        "requests_per_hour": req_per_h,
        "compute_usd_per_req": compute_per_req,
        "ops_usd_per_month": ops_month,
        "capacity_requests_per_month_per_box": capacity_month,
        "box_usd_per_month": box_month,
        "machines": machines,
        "monthly_usd": machines * box_month + ops_month,
    }


def build(per_item_path, out_path):
    rows = list(csv.DictReader(open(per_item_path, encoding="utf-8")))
    models = []
    for r in rows:
        if r["model"] not in models:
            models.append(r["model"])

    today_month = config.TODAY_REQUESTS_PER_DAY * 30
    summary, cost_model = [], {"assumptions": {"today_requests_per_day": config.TODAY_REQUESTS_PER_DAY,
                                               **config.SELF_HOST}, "models": {}}
    for m in models:
        mr = [r for r in rows if r["model"] == m]
        test = [r for r in mr if r.get("split") == "test"]
        lat = [_num(r["latency_ms"]) for r in mr if _num(r.get("latency_ms"))]
        tin = [_num(r["input_tokens"]) for r in mr if _num(r.get("input_tokens")) is not None]
        tout = [_num(r["output_tokens"]) for r in mr if _num(r.get("output_tokens")) is not None]
        tps = [_num(r["eval_tokens_per_s"]) for r in mr if _num(r.get("eval_tokens_per_s"))]
        name = next((r["model_name"] for r in mr if r.get("model_name")), m)
        mean_in = sum(tin) / len(tin) if tin else 0
        mean_out = sum(tout) / len(tout) if tout else 0
        mean_lat = sum(lat) / len(lat) if lat else None
        correct = sum(int(r["correct"]) for r in test)

        row = {
            "model": m, "model_name": name,
            "run_date": next((r["run_date"] for r in mr if r.get("run_date")), ""),
            "test_correct": correct, "test_total": len(test),
            "accuracy": f"{correct}/{len(test)}",
            "accuracy_pct": round(100 * correct / len(test), 1) if test else "",
            **{f: sum(1 for r in test if r["failure"] == f) for f in FAILURES},
            "calls_timed": len(lat),
            "p50_ms": percentile(lat, 50), "p95_ms": percentile(lat, 95),
            "mean_input_tokens": round(mean_in, 1), "mean_output_tokens": round(mean_out, 1),
            "tokens_per_s": round(sum(tps) / len(tps), 1) if tps else "",
        }

        price = config.PRICES_PER_MTOK.get(name)
        if price:
            per_req = (mean_in * price["input"] + mean_out * price["output"]) / 1e6
            cm = {"kind": "api", "usd_per_req": per_req,
                  "monthly_today": per_req * today_month, "monthly_100x": per_req * today_month * 100}
            row["cost_per_1k_usd"] = round(per_req * 1000, 4)
        elif mean_lat:
            today = local_costs(mean_lat, today_month)
            big = local_costs(mean_lat, today_month * 100)
            per_req_today = today["compute_usd_per_req"] + today["ops_usd_per_month"] / today_month
            cm = {"kind": "self_hosted", "usd_per_req": per_req_today, "today": today, "x100": big,
                  "monthly_today": today["monthly_usd"], "monthly_100x": big["monthly_usd"]}
            row["cost_per_1k_usd"] = round(per_req_today * 1000, 4)
        else:
            cm, row["cost_per_1k_usd"] = {"kind": "unknown"}, ""
        row["monthly_usd_today"] = round(cm.get("monthly_today", 0), 2)
        row["monthly_usd_100x"] = round(cm.get("monthly_100x", 0), 2)
        cost_model["models"][m] = {"model_name": name, **cm}
        summary.append(row)

    # Break-even: monthly volume where one dedicated self-hosted box costs the same as the API.
    local = next((v for v in cost_model["models"].values() if v.get("kind") == "self_hosted"), None)
    cost_model["break_even"] = {}
    if local:
        fixed = local["today"]["box_usd_per_month"] + local["today"]["ops_usd_per_month"]
        cap = local["today"]["capacity_requests_per_month_per_box"]
        for m, v in cost_model["models"].items():
            if v.get("kind") == "api" and v["usd_per_req"] > 0:
                vol = fixed / v["usd_per_req"]
                cost_model["break_even"][m] = {
                    "requests_per_month": vol, "requests_per_day": vol / 30,
                    "within_one_box_capacity": vol <= cap, "one_box_capacity_per_month": cap}

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    (out_path.parent / "cost_model.json").write_text(json.dumps(cost_model, indent=2), encoding="utf-8")

    print(f"{'model':<8}{'name':<20}{'acc':>7}{'p50':>8}{'p95':>8}{'$/1k':>10}{'$/mo 100x':>12}")
    for s in summary:
        print(f"{s['model']:<8}{s['model_name']:<20}{s['accuracy']:>7}{s['p50_ms'] or '':>8}"
              f"{s['p95_ms'] or '':>8}{s['cost_per_1k_usd']:>10}{s['monthly_usd_100x']:>12}")
    for m, b in cost_model["break_even"].items():
        print(f"break-even vs {m}: {b['requests_per_day']:,.0f} requests/day"
              f"{'' if b['within_one_box_capacity'] else ' (exceeds one box capacity)'}")
    print(f"-> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(config.RESULTS / "per_item.csv"))
    ap.add_argument("--out", default=str(config.RESULTS / "summary.csv"))
    args = ap.parse_args()
    build(args.inp, args.out)


if __name__ == "__main__":
    main()
