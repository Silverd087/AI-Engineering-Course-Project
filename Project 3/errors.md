# Error taxonomy

One row per error class: what goes wrong, what the agent does, and the test that shows it.
`error_type` values match `ErrorType` in `agent/tools/base.py`.

| Class | `error_type` | Example | What the agent does | Test |
|---|---|---|---|---|
| Tool down | `tool_unavailable` | | | |
| Bad arguments | `bad_arguments` | | | |
| Empty result | *(ok, empty)* | | | |
| Not found | `not_found` | | | |
| Path escape | `outside_workspace` | | | |
| Write not allowed | `not_allowed` | | | |
| Edit text not found / ambiguous | `no_match` / `ambiguous_match` | | | |
| Timeout | `timeout` | | | |
| Wrong tool | *(trajectory)* | | | |
| Loop | *(stop rule: looping)* | | | |
| User changes mind | `rejected_by_human` / quit | | | |

## Recovery-after-failure results

*To be filled in after `make eval`.*
