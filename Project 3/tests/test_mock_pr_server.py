from sandbox.mock_pr_server import MockPrServer


def test_open_pr_creates_pr_and_stores_it(tmp_path):
    server = MockPrServer(tmp_path / "prs.json")
    pr = server.open_pr("agent/utcnow", "Migrate utcnow", "Replaces utcnow.")
    assert pr["number"] == 1
    assert pr["state"] == "open"
    assert server.list_prs() == [pr]


def test_same_branch_returns_existing_pr(tmp_path):
    server = MockPrServer(tmp_path / "prs.json")
    first = server.open_pr("agent/utcnow", "Migrate utcnow", "body")
    second = server.open_pr("agent/utcnow", "A different title", "other body")
    assert second == first
    assert len(server.list_prs()) == 1


def test_different_branches_get_different_numbers(tmp_path):
    server = MockPrServer(tmp_path / "prs.json")
    a = server.open_pr("agent/one", "one", "b")
    b = server.open_pr("agent/two", "two", "b")
    assert (a["number"], b["number"]) == (1, 2)


def test_store_survives_a_new_server_object(tmp_path):
    path = tmp_path / "prs.json"
    MockPrServer(path).open_pr("agent/utcnow", "t", "b")
    assert [p["branch"] for p in MockPrServer(path).list_prs()] == ["agent/utcnow"]


def test_reset_clears_the_store(tmp_path):
    server = MockPrServer(tmp_path / "prs.json")
    server.open_pr("agent/utcnow", "t", "b")
    server.reset()
    assert server.list_prs() == []


def test_save_leaves_no_temp_file_behind(tmp_path):
    server = MockPrServer(tmp_path / "prs.json")
    server.open_pr("agent/utcnow", "t", "b")
    assert not (tmp_path / "prs.tmp").exists()