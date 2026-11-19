# Cost model

## What is measured

- **Tokens and USD per model call.** Taken from the API's usage data and priced with `PRICE_INPUT_PER_MTOK` and `PRICE_OUTPUT_PER_MTOK` from `.env`.
- **Per step.** Each tool step in the trace carries the cost of the model call that requested it. When one reply requests several tool calls, the cost goes on the first one and the others carry zero, so no model call is counted twice.
- **Per run, final call.** The model call that ends the run has its own trace record: `finish` if the model called finish, `reply` if it answered without a tool, or `stopped` if a limit was hit while tool calls were still pending.
- **Per run, quit.** If a human quits at a write that isn't the reply's first call, the reply's cost goes in a `quit` record, because the first call never ran.
- **Reconciliation.** The trace records add up to the run total in `state.cost_usd`. A test checks this for normal runs and for a quit.

## How cost is used

- **Budget rule.** `MAX_COST_USD` stops the run once the total reaches the limit.
- **Eval metrics.** Mean cost per task, total cost, and cost at 100x (mean cost times 100).

## Pricing

- Prices come from `.env`. The defaults are 0, which makes every cost 0 and turns the budget rule off in practice.
- Set them from the provider's price page for the model used, and record the date you checked them.

## Gaps

1. **Failed model calls are not costed.** If the API call raises (rate limit, network error, bad key), there is no response, so no tokens or cost are recorded. The provider can still bill the attempt. The eval row records the error, but not the cost.
2. **LangSmith numbers are separate.** If tracing is on, LangSmith shows its own token counts. Those are not used in this report.

## Results

*To be filled in after `make eval`.*

| Metric | Value |
|---|---|
| Model | |
| Prices used (USD per 1M input / output tokens, date checked) | |
| Mean cost per task (USD) | |
| Total cost, all scenarios (USD) | |
| Cost at 100x (USD) | |
| Mean tokens in / out per task | |
| p50 / p95 seconds per task | |