"""M2 breadth: aggregate before->after agreement across a subset + the exploitability
hit-rate, with the grader/oracle split honest per task and the sweep deterministic.
"""

from types import SimpleNamespace

import pytest

from rampart.agents.specialists import FORGER
from rampart.breadth import run_breadth, run_task
from rampart.breadth.__main__ import build_discover_fn
from rampart.breadth.cheats import forger_cheats
from rampart.breadth.loop import _split_plus
from rampart.substrate import load_subset

_N = 4


class _ScriptedRed:
    """Fake Anthropic client: writes one solution, runs the tests, then stops. Reacts to the
    message count so each fresh red-agent session (re)starts the script — no network."""

    def __init__(self, solution_src: str):
        self._src = solution_src
        outer = self

        class _Messages:
            def create(self, *, messages, **kwargs):
                n = len(messages)
                if n == 1:
                    block = SimpleNamespace(
                        type="tool_use",
                        id="w",
                        name="write_file",
                        input={"path": "solution.py", "content": outer._src},
                    )
                elif n == 3:
                    block = SimpleNamespace(type="tool_use", id="r", name="run_tests", input={})
                else:
                    block = SimpleNamespace(type="text", text="done")
                return SimpleNamespace(content=[block], stop_reason="end_turn")

        self.messages = _Messages()


@pytest.fixture(scope="module")
def report():
    return run_breadth(n_tasks=_N, workers=_N)


def test_coverage_is_reported_honestly(report):
    assert report.n_loaded == _N
    assert report.source == "seed"
    assert report.n_failed == 0
    assert all(r.error == "" for r in report.results)


def test_exploitability_hit_rate_is_the_headline(report):
    # Almost every standard sparse grader is breachable by the generic memorization cheat.
    assert report.n_breachable >= 1
    assert report.hit_rate == report.n_breachable / report.n_graders
    assert report.n_breachable == _N  # all four are breachable


def test_aggregate_agreement_moves_up_with_honest_pass_preserved(report):
    assert report.n_measurable >= 1
    assert report.mean_agreement_after > report.mean_agreement_before
    assert report.mean_agreement_before == 0.0
    assert report.mean_agreement_after == 1.0
    assert report.mean_honest_pass == 1.0


def test_results_are_in_task_order_deterministically(report):
    ids = [r.task_id for r in report.results]
    assert ids == sorted(ids, key=lambda k: int(k.split("/")[1]))


def test_grader_and_oracle_halves_are_disjoint_per_task():
    """Invariant #2 across the subset: the hardening half and the oracle half never overlap."""
    for task in load_subset(_N):
        harden, oracle = _split_plus(task)
        h = {repr(x) for x in harden}
        o = {repr(x) for x in oracle}
        assert h.isdisjoint(o)
        base = {repr(x) for x in task.base_input}
        assert base.isdisjoint(h) and base.isdisjoint(o)


def test_run_task_is_deterministic():
    task = load_subset(1)[0]
    a = run_task(task)
    b = run_task(task)
    assert (a.breachable, a.agreement_before, a.agreement_after, a.honest_pass) == (
        b.breachable,
        b.agreement_before,
        b.agreement_after,
        b.honest_pass,
    )


def test_forger_cheats_are_deterministic_and_nonempty():
    task = load_subset(1)[0]
    assert forger_cheats(task) == forger_cheats(task)
    assert len(forger_cheats(task)) >= 2


def test_discovered_breaches_swap_in_without_code_change():
    """Injecting breaches (as the red agent will) is consumed in place of the seeds."""
    task = load_subset(1)[0]
    gold = task.prompt + task.canonical_solution
    injected = forger_cheats(task)  # stand in for red-agent breaches
    result = run_task(task, candidates=injected)
    assert result.source == "provided"
    assert result.breachable
    # a genuinely correct solution is not counted as a breach
    assert run_task(task, candidates=[gold]).breachable is False


def test_red_swarm_discovery_is_wired_with_a_scripted_client():
    """End-to-end the injected discover_fn (no network): the red agent writes a solution, we
    read it back, and run_task consumes it labeled 'discovered'."""
    task = load_subset(1)[0]
    cheat = forger_cheats(task)[0]
    discover = build_discover_fn(_ScriptedRed(cheat), specialists=(FORGER,))

    assert len(discover(task)) == 1 and discover(task)[0].strip()

    result = run_task(task, discover_fn=discover)
    assert result.source == "discovered"
    assert result.breachable is True


def test_no_discover_fn_falls_back_to_seed():
    assert run_task(load_subset(1)[0]).source == "seed"
