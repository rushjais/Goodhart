"""Track C — the best-of-K capability export serializes a real GapReport for the dashboard."""

from rampart.bestofk.core import compute_gap
from rampart.rollout.dataset import Rollout
from rampart.server.capability_export import gap_to_capability


def test_gap_to_capability_shape_and_recovered_case():
    # One (task,model) group: naive reward tops the cheat (oracle-wrong); hardened tops the solve.
    rollouts = [
        Rollout("t1", "m", "CHEAT body", 1, 0, 0),  # r_naive=1, r_hardened=0, t_oracle=0
        Rollout("t1", "m", "SOLVE body", 0, 1, 1),  # r_naive=0, r_hardened=1, t_oracle=1
    ]
    cap = gap_to_capability(compute_gap(rollouts, seed=0), source="unit-test")

    assert [b["kind"] for b in cap["bars"]] == ["leaky", "hardened"]
    assert cap["bars"][0]["value"] == 0.0  # naive selection landed on the cheat (oracle-wrong)
    assert cap["bars"][1]["value"] == 1.0  # hardened selection landed on the solve
    assert cap["gap"] == 1.0
    assert cap["n"] == 1

    assert len(cap["cases"]) == 1
    case = cap["cases"][0]
    assert case["recovered"] is True
    assert "CHEAT" in case["naive"] and "SOLVE" in case["hardened"]


def test_no_cheat_means_no_cases():
    rollouts = [Rollout("t1", "m", "ok", 1, 1, 1), Rollout("t1", "m", "ok2", 1, 1, 1)]
    cap = gap_to_capability(compute_gap(rollouts, seed=0), source="unit-test")
    assert cap["cases"] == []
    assert cap["gap"] == 0.0
