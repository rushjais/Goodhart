"""Smoke test for the locked seams: the contract imports and behaves as specified.

The front half of Seam 1 (load_task, make_workdir, run_grader, is_breach) is wired to
Track A's real impls; the back half (oracle, patch, gate, metrics) is not built yet.
"""

import pytest

from rampart import events, grader, harness, substrate
from rampart.loop import interface

# Not built yet — still contract stubs.
NOT_BUILT = [
    (interface.run_oracle, ("workdir",)),
    (interface.apply_patch, ("grader", "tpl", {})),
    (interface.regression_gate, ("grader_prime", "breach", "gold")),
    (interface.agreement, ("grader", set())),
    (interface.honest_pass, ("grader", set())),
]


@pytest.mark.parametrize("fn, args", NOT_BUILT)
def test_unbuilt_seam_stubs_raise_not_implemented(fn, args):
    with pytest.raises(NotImplementedError):
        fn(*args)


def test_wired_seam_delegates_to_real_impls():
    # The seam IS the single entrypoint — it re-exports Track A's implementations.
    assert interface.load_task is substrate.load_task
    assert interface.make_workdir is harness.make_workdir
    assert interface.run_grader is grader.run_grader
    assert interface.Task is substrate.Task


def test_is_breach_is_grader_pass_and_oracle_fail():
    assert interface.is_breach(1, 0) is True
    assert interface.is_breach(1, 1) is False
    assert interface.is_breach(0, 0) is False
    assert interface.is_breach(0, 1) is False


def test_seam2_events_construct_with_verbatim_type_tags():
    assert events.AgentSpawn("forger", "hardcode").type == "agent_spawn"
    assert events.AgentMove("forger", "gate1").type == "agent_move"
    breach = events.BreachFound("forger", "gate1", "hardcode", 1, 0, "return []")
    assert breach.type == "breach_found"
    assert events.PatchApplied("gate1", "pristine_copy").type == "patch_applied"
    assert events.PatchRejected("gate1", "hit honest solution").type == "patch_rejected"
    assert events.AgentKilled("forger", "gate1").type == "agent_killed"
    assert events.RobustnessUpdate(0.97, 1.0, 40).type == "robustness_update"
