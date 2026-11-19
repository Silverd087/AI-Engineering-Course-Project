"""Child process for search_code: walks the workspace and matches the regex.

Runs in its own process so the parent can stop it after a time limit.
Reads one JSON request from stdin and prints one JSON result to stdout.
"""

import json
import re
import sys
from pathlib import Path

from agent.tools.denylist import is_secret_path

MAX_MATCHES = 100
MAX_LINE_CHARS = 200
MAX_FILE_BYTES = 1_000_000


def run_search(workspace: str, pattern: str, glob: str) -> dict:
    regex = re.compile(pattern)
    root = Path(workspace).resolve()
    matches = []
    total = 0
    for path in sorted(root.glob(glob)):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            continue  # a symlink that points outside the workspace
        rel = path.relative_to(root)
        if ".git" in rel.parts or is_secret_path(rel.as_posix()):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue  # too large to be source code worth searching
        data = path.read_bytes()
        if b"\x00" in data[:8000]:
            continue  # binary file
        text = data.decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                total += 1
                if len(matches) < MAX_MATCHES:
                    matches.append({
                        "path": rel.as_posix(),
                        "line": number,
                        "text": line.strip()[:MAX_LINE_CHARS],
                    })
    return {"matches": matches, "total": total, "truncated": total > MAX_MATCHES}


def main() -> None:
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    print(json.dumps(run_search(request["workspace"], request["pattern"], request["glob"])))


if __name__ == "__main__":
    main()