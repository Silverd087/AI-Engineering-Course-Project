# Error taxonomy

One row per error class: what goes wrong, what the agent does, and the test that shows it.
`error_type` values match `ErrorType` in `agent/tools/base.py`.

| Class | `error_type` | Example | What the agent does | Test |
|---|---|---|---|---|
| Tool down | `tool_unavailable` | `read_file` fails once (fault `down`) | Reads the hint "try again, or use another tool" and continues | `tests/test_faults.py::test_down_is_tool_unavailable` |
| Bad arguments | `bad_arguments` | `read_file` called with an unknown field | Gets the error and retries with valid fields | `tests/test_read_file.py::test_unknown_argument_is_rejected` |
| Empty result | *(ok, empty)* | fault `empty` returns `{}` | Treats it as success with no data | `tests/test_faults.py::test_empty_is_success_with_empty_result` |
| Not found | `not_found` | `read_file` on a missing path | Uses `list_files`, as the hint says | `tests/test_read_file.py::test_missing_file_is_not_found` |
| Path escape | `outside_workspace` | `read_file` on `../secret.txt` | Refused; retries with a path inside the repo | `tests/test_read_file.py::test_path_outside_workspace_is_refused` |
| Write not allowed | `not_allowed` | `edit_file` on a file outside `allowed_files` | Refused; the file is not touched | `tests/test_edit_file.py::test_file_outside_allowed_patterns_is_refused` |
| Edit text not found / ambiguous | `no_match` / `ambiguous_match` | `old` text missing, or found twice | Refused, file unchanged; retries with more specific text | `tests/test_edit_file.py::test_missing_text_is_no_match_and_file_is_unchanged`; `tests/test_edit_file.py::test_repeated_text_is_ambiguous_and_file_is_unchanged` |
| Timeout | `timeout` | `run_tests` takes longer than the limit | Gets the hint to run a smaller target | `tests/test_errors.py::test_run_tests_timeout_becomes_timeout_error` |
| Tool crash | `internal_error` | a tool raises an exception | Gets a generic message; the exception text is not shown to the model | `tests/test_errors.py::test_crashing_tool_becomes_internal_error_without_leaking_details` |
| Wrong tool | *(trajectory)* | a call to a tool name that doesn't exist | Gets `not_found`; the step is counted as wasted in the metrics | `tests/test_tools_node.py::test_unknown_tool_returns_not_found` |
| Loop | *(stop rule: looping)* | the same call made `max_repeats` times in a row | The run stops with `stop_reason` = looping | `tests/test_stop.py::test_looping_after_max_repeats_identical_calls` |
| User changes mind | `rejected_by_human` / quit | the human answers `n` or `q` at the checkpoint | `n`: the write is skipped and the model is told; `q`: the run ends | `tests/test_approval.py::test_rejected_write_does_not_run_and_model_is_told`; `tests/test_approval.py::test_quit_ends_the_run_without_running_the_write` |

## Recovery-after-failure results

*To be filled in after `make eval`.*