import json

from agent.nodes import WRITE_TOOLS
from agent.tools import build_tools
from sandbox.mock_pr_server import MockPrServer


def registry(tmp_path):
    return build_tools(["src/**"], MockPrServer(tmp_path / "prs.json"))


def test_every_executable_tool_has_a_schema(tmp_path):
    schemas, functions = registry(tmp_path)
    names = {s["function"]["name"] for s in schemas}
    assert set(functions) <= names


def test_only_finish_has_no_function(tmp_path):
    schemas, functions = registry(tmp_path)
    names = {s["function"]["name"] for s in schemas}
    assert names - set(functions) == {"finish"}


def test_write_tools_are_registered(tmp_path):
    _, functions = registry(tmp_path)
    assert WRITE_TOOLS <= set(functions)


def test_schemas_reject_unknown_fields(tmp_path):
    schemas, _ = registry(tmp_path)
    for schema in schemas:
        assert schema["function"]["parameters"]["additionalProperties"] is False, schema["function"]["name"]


def test_schemas_are_json_serialisable(tmp_path):
    schemas, _ = registry(tmp_path)
    json.dumps(schemas)


def test_finish_only_allows_success_or_gave_up(tmp_path):
    schemas, _ = registry(tmp_path)
    finish = next(s for s in schemas if s["function"]["name"] == "finish")
    status = finish["function"]["parameters"]["properties"]["status"]
    assert set(status.get("enum", [])) == {"success", "gave_up"}