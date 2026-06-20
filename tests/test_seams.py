"""Smoke test for the locked seams: the contract imports and behaves as specified."""

import pytest

from rampart import events
from rampart.loop import interface

SEAM1 = [
    (interface.load_task, ("HumanEval/0",)),
    (interface.make_workdir, ({},)),
    (interface.run_grader, ("workdir",)),
    (interface.run_oracle, ("workdir",)),
    (interface.is_breach, (1, 0)),
    (interface.apply_patch, ("grader", "tpl", {})),
    (interface.regression_gate, ("grader_prime", "breach", "gold")),
    (interface.agreement, ("grader", set())),
    (interface.honest_pass, ("grader", set())),
]


@pytest.mark.parametrize("fn, args", SEAM1)
def test_seam1_stubs_raise_not_implemented(fn, args):
    with pytest.raises(NotImplementedError):
        fn(*args)


def test_seam2_events_construct_with_verbatim_type_tags():
    assert events.AgentSpawn("forger", "hardcode").type == "agent_spawn"
    assert events.AgentMove("forger", "gate1").type == "agent_move"
    breach = events.BreachFound("forger", "gate1", "hardcode", 1, 0, "return []")
    assert breach.type == "breach_found"
    assert events.PatchApplied("gate1", "pristine_copy").type == "patch_applied"
    assert events.PatchRejected("gate1", "hit honest solution").type == "patch_rejected"
    assert events.AgentKilled("forger", "gate1").type == "agent_killed"
    assert events.RobustnessUpdate(0.97, 1.0, 40).type == "robustness_update"
