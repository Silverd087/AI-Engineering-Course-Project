# Threat model: injection through tool output

## Assets
What an attacker could damage: source files in the workspace, the PR (title/body/branch), the human's trust in the diff, the API budget.

## Where untrusted text enters

| Entry point | Tool | Example payload |
|---|---|---|
| Code comments / docstrings | `read_file`, `search_code` | |
| Test output (assert messages, prints) | `run_tests` | |
| README / docs in the repo | `read_file` | |
| PR template | `open_pull_request` | |
| Error messages from tools | any | |

## Mitigations
- Data vs instructions: `<untrusted_tool_output>` wrapping and the system prompt
- Least privilege: no shell, no network, path jail, `allowed_files`
- Human checkpoint before every write
- Idempotent writes, stop rule and budget

## Injection test cases and results

*At least 5 cases, see `eval/scenarios/injection_*.yaml`. Results to be filled in.*
