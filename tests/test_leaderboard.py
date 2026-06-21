from starlette.testclient import TestClient

from rampart.server.leaderboard import create_leaderboard_app
from rampart.server.seed import seed_board


def _sub(env_name, naive_fa, hardened_fa=0.0):
    """A submission whose naive false-accept = naive_fa (the headline gameability)."""
    return {
        "env_name": env_name,
        "substrate": "custom",
        "n_completions": 10,
        "n_exploits": 4,
        "verifiers": [
            {
                "name": "naive",
                "safety_score": 50.0,
                "catch_rate": 1 - naive_fa,
                "false_accept": naive_fa,
                "honest_pass": 1.0,
                "agreement": 0.6,
                "best_of_k": 0.4,
            },
            {
                "name": "hardened",
                "safety_score": 100.0,
                "catch_rate": 1 - hardened_fa,
                "false_accept": hardened_fa,
                "honest_pass": 1.0,
                "agreement": 1.0,
                "best_of_k": 1.0,
            },
        ],
        "examples": [
            {
                "task_id": "t/0",
                "kind": "naive_accepted_cheat",
                "completion": "cheat",
                "r_naive": 1,
                "r_hardened": 0,
                "t_oracle": 0,
            }
        ],
    }


def _client(tmp_path):
    return TestClient(create_leaderboard_app(str(tmp_path / "board.db")))


def test_submit_then_rank_then_detail(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/submit", json=_sub("my-env", naive_fa=0.9))
    assert r.status_code == 200
    sid = r.json()["id"]
    assert r.json()["url"].endswith(f"/env/{sid}")

    board = c.get("/api/leaderboard").json()
    assert board["sort"] == "gameable"
    assert any(row["env_name"] == "my-env" and row["rank"] == 1 for row in board["rows"])

    detail = c.get(f"/api/env/{sid}").json()
    assert detail["env_name"] == "my-env"
    assert {v["name"] for v in detail["verifiers"]} == {"naive", "hardened"}
    assert detail["gap"] == {"naive": 0.4, "hardened": 1.0}
    assert detail["examples"][0]["kind"] == "naive_accepted_cheat"
    assert detail["board_rank"] == 1


def test_unknown_env_404(tmp_path):
    assert _client(tmp_path).get("/api/env/nope").status_code == 404


def test_missing_naive_row_422(tmp_path):
    bad = _sub("x", 0.5)
    bad["verifiers"] = [v for v in bad["verifiers"] if v["name"] != "naive"]
    assert _client(tmp_path).post("/api/submit", json=bad).status_code == 422


def test_more_gameable_ranks_above_hardened(tmp_path):
    c = _client(tmp_path)
    c.post("/api/submit", json=_sub("leaky-env", naive_fa=0.9))
    c.post("/api/submit", json=_sub("tight-env", naive_fa=0.1))
    rows = c.get("/api/leaderboard?sort=gameable").json()["rows"]
    names = [r["env_name"] for r in rows]
    assert names.index("leaky-env") < names.index("tight-env")  # most-gameable first


def test_seed_populates_board(tmp_path):
    db = str(tmp_path / "seed.db")
    n = seed_board(db)
    c = TestClient(create_leaderboard_app(db))
    rows = c.get("/api/leaderboard").json()["rows"]
    assert len(rows) == n
    assert any(r["verified"] for r in rows)  # canonical seeds are verified
