"""Tool registry: the schemas the model sees, and the functions that run them.

Each tool is a plain function (workspace, args) -> ToolResult with a Pydantic args model.

Read:  list_files, read_file, search_code
Exec:  run_tests
Write: edit_file, open_pull_request   (go through the human checkpoint)
Done:  finish

build_tools() is the one place that decides which tools exist for a run.
"""

from agent.tools.edit_file import EditFileArgs, make_edit_file
from agent.tools.finish import FinishArgs
from agent.tools.list_files import ListFilesArgs, list_files
from agent.tools.open_pull_request import OpenPullRequestArgs, make_open_pull_request
from agent.tools.read_file import ReadFileArgs, read_file
from agent.tools.run_tests import RunTestsArgs, run_tests
from agent.tools.search_code import SearchCodeArgs, search_code


def _schema(name: str, description: str, args_model) -> dict:
    # The OpenAI function format, which ChatOpenAI.bind_tools accepts directly.
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": args_model.model_json_schema(),
        },
    }


def build_tools(allowed_files: list[str], pr_api) -> tuple[list[dict], dict]:
    """Return (schemas for the model, functions for the graph) for one run."""
    functions = {
        "read_file": read_file,
        "list_files": list_files,
        "search_code": search_code,
        "run_tests": run_tests,
        "edit_file": make_edit_file(allowed_files),
        "open_pull_request": make_open_pull_request(pr_api),
    }
    schemas = [
        _schema(
            "read_file",
            "Read a file in the repository. Optionally give start_line and end_line (1-based, inclusive).",
            ReadFileArgs,
        ),
        _schema(
            "list_files",
            "List files in the repository matching a glob such as 'src/**/*.py'.",
            ListFilesArgs,
        ),
        _schema(
            "search_code",
            "Search files in the repository for lines matching a regular expression. Optionally limit with a glob.",
            SearchCodeArgs,
        ),
        _schema(
            "run_tests",
            "Run the test suite, or one test file or folder, with warnings treated as errors. Returns the output.",
            RunTestsArgs,
        ),
        _schema(
            "edit_file",
            "Replace one exact piece of text in an allowed file. 'old' must appear exactly once. Needs human approval.",
            EditFileArgs,
        ),
        _schema(
            "open_pull_request",
            "Commit the changes to an 'agent/' branch, push it, and open a pull request. Needs human approval.",
            OpenPullRequestArgs,
        ),
        _schema(
            "finish",
            "End the run. Use status 'success' when the migration is complete, or 'gave_up' if it cannot be completed.",
            FinishArgs,
        ),
    ]
    return schemas, functions