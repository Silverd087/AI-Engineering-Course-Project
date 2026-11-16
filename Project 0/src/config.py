"""Single place for every setting shared by run.py, cost.py and the web app.

Model names can be overridden with environment variables so nobody edits code
to swap a model -- but whatever you run, record it in the report.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Optional: read KEY=VALUE lines from Project 0/.env (git-ignored). Real env vars win.
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
DATA = ROOT / "data"
RESULTS = Path(os.environ.get("BAKEOFF_RESULTS", ROOT / "results"))
ITEMS_PATH = DATA / "items.jsonl"
DB_PATH = DATA / "bookstore.db"
SCHEMA_PATH = DATA / "schema.sql"
PROMPT_PATH = Path(__file__).resolve().parent / "prompt.txt"

# Identical generation settings for all three models.
MAX_OUTPUT_TOKENS = 2048      # same output cap for every model
REQUEST_TIMEOUT_S = 120       # a request slower than this counts as a timeout (wrong)
TEMPERATURE = 0               # sent to every model that accepts it
REASONING_EFFORT = "low"      # OpenAI reasoning models (gpt-5*, o*) only: they reject temperature and
                              # always reason, so both API models get the same, lowest effort level.
# NOTE: OpenAI reasoning models reject `temperature` other than the default, so they run at
# their fixed default sampling. This is the one setting we could not make identical; it is
# documented in the report. Non-reasoning models (e.g. gpt-4.1*) get temperature 0.

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Exact names go in the report. Override without editing code: TOP_MODEL=... CHEAP_MODEL=...
MODELS = {
    "top":   {"provider": "openai", "name": os.environ.get("TOP_MODEL", "gpt-5")},
    "cheap": {"provider": "openai", "name": os.environ.get("CHEAP_MODEL", "gpt-5-mini")},
    "local": {"provider": "ollama", "name": os.environ.get("LOCAL_MODEL", "qwen2.5-coder:7b")},
}


def is_reasoning_model(name):
    return name.startswith(("gpt-5", "o1", "o3", "o4"))


# List prices, USD per 1M tokens, from https://openai.com/api/pricing .
# VERIFY against the pricing page on the day you run, and add a row if you change models:
# cost.py leaves the cost blank for a model with no price here.
PRICES_PER_MTOK = {
    "gpt-5":       {"input": 1.25, "output": 10.00},
    "gpt-5-mini":  {"input": 0.25, "output": 2.00},
    "gpt-5-nano":  {"input": 0.05, "output": 0.40},
    "gpt-4.1":     {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}

# Self-hosting cost model (edit to match your own machine; every number is an assumption
# and is printed in summary.csv so the reader can see it).
SELF_HOST = {
    "hardware_price_usd": 1300.0,   # RTX 4060 laptop
    "hardware_life_hours": 3 * 365 * 8,  # 3 years at 8 h/day
    "power_kw": 0.14,               # laptop at full GPU load
    "electricity_usd_per_kwh": 0.20,
    "ops_hours_per_month": 4.0,     # updates, restarts, monitoring
    "engineer_usd_per_hour": 25.0,
    # For the break-even estimate: a dedicated always-on box doing nothing else.
    "dedicated_hours_per_month": 730,
}

# Traffic assumption for "today" and "100x". 1,000 requests/day is a small internal tool.
TODAY_REQUESTS_PER_DAY = 1000
