from __future__ import annotations

import math
from collections.abc import Sequence


def first_relevant_rank(retrieved_ids: Sequence[str], relevant_ids: set[str]) -> int | None:
    """1-based rank of the first relevant chunk, or None if none was retrieved."""
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return rank
    return None


def hit_at_k(ranks: Sequence[int | None], k: int) -> float:
    """Share of questions whose first relevant chunk is within the top k."""
    if not ranks:
        return 0.0
    hits = sum(1 for r in ranks if r is not None and r <= k)
    return hits / len(ranks)


def mrr(ranks: Sequence[int | None]) -> float:
    """Mean reciprocal rank. A question with no relevant chunk contributes 0."""
    if not ranks:
        return 0.0
    return sum(1.0 / r for r in ranks if r is not None) / len(ranks)


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile. p is between 0 and 100."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(p / 100 * len(ordered)) - 1))
    return ordered[idx]


def cost_per_request(
    input_tokens: int,
    output_tokens: int,
    price_in_per_million: float,
    price_out_per_million: float,
    fixed_per_request: float = 0.0,
) -> float:
    """Model cost for one request, plus any fixed per-request cost such as embedding calls."""
    token_cost = (
        input_tokens * price_in_per_million + output_tokens * price_out_per_million
    ) / 1_000_000
    return token_cost + fixed_per_request


def projected_monthly_cost(
    cost_per_req: float,
    requests_per_month: int,
    fixed_monthly: float = 0.0,
) -> float:
    """Monthly cost. Per-request cost scales with traffic; infrastructure cost stays fixed."""
    return cost_per_req * requests_per_month + fixed_monthly