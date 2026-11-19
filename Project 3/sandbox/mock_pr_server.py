"""Mock PR API (task B3).

TODO: file-backed store in sandbox/prs/prs.json.
- open_pr(branch, title, body) -> PR: idempotent by branch (2nd call returns the existing PR)
- list_prs(), reset()
"""

"""Mock PR API (task B3): a file-backed pull request store for local runs and evals.

Stands in for GitHub's pull request API. It never touches the network.
The store is sandbox/prs/prs.json, and `make sandbox-reset` deletes it.
"""

import json
import os
from pathlib import Path

DEFAULT_STORE = Path(__file__).resolve().parent / "prs" / "prs.json"


class MockPrServer:
    def __init__(self, store_path: Path = DEFAULT_STORE) -> None:
        self.store_path = Path(store_path)

    def _load(self) -> dict:
        if not self.store_path.exists():
            return {"next_number": 1, "prs": []}
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.store_path)  # replaces the file in one step, so a crash never leaves half a file

    def open_pr(self, branch: str, title: str, body: str) -> dict:
        data = self._load()
        for pr in data["prs"]:
            if pr["branch"] == branch:
                return pr  # idempotent: one PR per branch, the first title and body win
        pr = {
            "number": data["next_number"],
            "branch": branch,
            "title": title,
            "body": body,
            "state": "open",
        }
        data["prs"].append(pr)
        data["next_number"] += 1
        self._save(data)
        return pr

    def list_prs(self) -> list[dict]:
        return list(self._load()["prs"])

    def reset(self) -> None:
        if self.store_path.exists():
            self.store_path.unlink()


if __name__ == "__main__":
    import sys

    server = MockPrServer()
    if sys.argv[1:] == ["list"]:
        for pr in server.list_prs():
            print(f"#{pr['number']} {pr['branch']}: {pr['title']}")
    elif sys.argv[1:] == ["reset"]:
        server.reset()
        print("Mock PR store cleared.")
    else:
        raise SystemExit("Usage: python -m sandbox.mock_pr_server [list|reset]")