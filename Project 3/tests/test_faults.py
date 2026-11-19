import pytest

from agent.tools.base import ErrorType, ToolResult
from eval.faults import fault_result, inject_faults
from eval.schema import Fault


def real_read(workspace, args):
    return ToolResult.success({"content": "real"})


def fault(tool, at_call, kind):
    return Fault(tool=tool, at_call=at_call, kind=kind)


def test_down_is_tool_unavailable():
    assert fault_result("read_file", "down").error_type == ErrorType.TOOL_UNAVAILABLE


def test_timeout_is_timeout():
    assert fault_result("run_tests", "timeout").error_type == ErrorType.TIMEOUT


def test_server_error_mentions_500():
    result = fault_result("open_pull_request", "server_error")
    assert result.error_type == ErrorType.TOOL_UNAVAILABLE
    assert "500" in result.message


def test_empty_is_success_with_empty_result():
    result = fault_result("search_code", "empty")
    assert result.ok and result.result == {}


def test_bad_output_is_success_but_garbled():
    result = fault_result("read_file", "bad_output")
    assert result.ok and "garbled" in result.result


def test_unknown_kind_is_an_error():
    with pytest.raises(ValueError, match="Unknown fault kind"):
        fault_result("read_file", "explode")


def test_only_the_chosen_call_fails():
    wrapped = inject_faults({"read_file": real_read}, [fault("read_file", 2, "down")])
    assert wrapped["read_file"]("ws", {}).ok
    assert wrapped["read_file"]("ws", {}).error_type == ErrorType.TOOL_UNAVAILABLE
    assert wrapped["read_file"]("ws", {}).ok


def test_faulted_call_does_not_run_the_real_tool():
    ran = []

    def recording(workspace, args):
        ran.append(args)
        return ToolResult.success({})

    wrapped = inject_faults({"edit_file": recording}, [fault("edit_file", 1, "timeout")])
    wrapped["edit_file"]("ws", {"path": "a.py"})
    assert ran == []


def test_several_faults_on_one_tool_all_apply():
    wrapped = inject_faults(
        {"read_file": real_read},
        [fault("read_file", 1, "down"), fault("read_file", 3, "empty")],
    )
    assert wrapped["read_file"]("ws", {}).error_type == ErrorType.TOOL_UNAVAILABLE
    assert wrapped["read_file"]("ws", {}).ok
    assert wrapped["read_file"]("ws", {}).result == {}


def test_fault_for_unknown_tool_is_rejected_early():
    with pytest.raises(ValueError, match="unknown tool"):
        inject_faults({"read_file": real_read}, [fault("nope", 1, "down")])


def test_untouched_tools_are_returned_as_they_were():
    wrapped = inject_faults({"read_file": real_read, "list_files": real_read}, [fault("read_file", 1, "down")])
    assert wrapped["list_files"] is real_read