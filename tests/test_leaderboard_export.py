"""Track C — the env-ranked leaderboard exporter: real rows from rollouts, placeholders else."""

import json

from rampart.server.leaderboard_export import build, domain_for, real_row


def _write(p, rows):
    p.write_text("\n".join(json.dumps(r) for r in rows))


def test_real_row_scores_a_rollouts_file(tmp_path):
    f = tmp_path / "r.jsonl"
    _write(
        f,
        [
            {
                "task_id": "t1",
                "model": "m",
                "completion": "x",
                "r_naive": 1,
                "r_hardened": 0,
                "t_oracle": 0,
            },  # cheat naive accepts
            {
                "task_id": "t1",
                "model": "m",
                "completion": "y",
                "r_naive": 1,
                "r_hardened": 1,
                "t_oracle": 1,
            },  # honest
        ],
    )
    row = real_row("evalplus", str(f))
    assert row["placeholder"] is False
    assert row["domain"] == "code"
    assert row["naive"]["catch_rate"] == 0.0  # naive rejected none of the cheats
    assert row["gameability"] == 1.0  # 1 - naive catch
    assert row["hardened"]["catch_rate"] == 1.0


def test_build_mixes_real_and_placeholder_and_ranks_by_gameability(tmp_path):
    f = tmp_path / "e.jsonl"
    _write(
        f,
        [
            {
                "task_id": "t1",
                "model": "m",
                "completion": "x",
                "r_naive": 0,
                "r_hardened": 0,
                "t_oracle": 0,
            },  # cheat naive rejects -> low gameability
            {
                "task_id": "t1",
                "model": "m",
                "completion": "y",
                "r_naive": 1,
                "r_hardened": 1,
                "t_oracle": 1,
            },
        ],
    )
    payload = build([("evalplus", str(f)), ("rg:gsm_symbolic", "definitely/missing.jsonl")])
    assert payload["has_placeholders"] is True
    assert payload["real_envs"] == 1
    envs = payload["environments"]
    # rg placeholder gameability (0.9) > evalplus real gameability (0.0) -> rg ranked first
    assert envs[0]["env"] == "rg:gsm_symbolic" and envs[0]["placeholder"] is True
    assert envs[1]["env"] == "evalplus" and envs[1]["placeholder"] is False


def test_all_placeholder_when_no_data():
    payload = build([("evalplus", "nope.jsonl"), ("rg:gsm_symbolic", "nope.jsonl")])
    assert payload["real_envs"] == 0
    assert all(e["placeholder"] for e in payload["environments"])


def test_domain_for():
    assert domain_for("evalplus") == "code"
    assert domain_for("rg:gsm_symbolic") == "math"
    assert domain_for("mystery-env") == "other"
