"""Wire the conductor's injected fns to the real loop: gate = EvalPlus task_id.

probe   = make a workdir and run the specialist against the real grader.
verify  = Gatekeep: confirm R=1 AND T=0 (deterministic) and not on the (empty) seed list.
seal    = the LLM green team hardens the grader.
regrade = score a breach under a patched grader (for Invalidate).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..agents.red import SEED_LIST
from ..agents.specialists import Specialist, run_specialist
from ..green import harden
from ..loop import interface
from ..templates import grade
from .core import ConductorReport, SealResult, run_conductor


def make_runners(client: Any = None):
    """Return (probe, verify, seal, regrade) closed over the real seam + agents + green."""

    def probe(gate: str, specialist: Specialist) -> dict | None:
        task = interface.load_task(gate)
        workdir = interface.make_workdir(task)
        run_specialist(specialist, workdir, run_tests=interface.run_grader, client=client)
        if interface.run_grader(workdir) != 1:
            return None
        source = (Path(workdir) / "solution.py").read_text()
        return {
            "source": source,
            "example": source.strip().splitlines()[-1][:120] if source.strip() else "",
            "task": task,
            "workdir": str(workdir),
            "gold": task.prompt + task.canonical_solution,
        }

    def verify(gate: str, candidate: dict) -> bool:
        r = interface.run_grader(candidate["workdir"])
        t = interface.run_oracle(candidate["task"], candidate["workdir"])
        return interface.is_breach(r, t) and candidate["source"] not in SEED_LIST

    def seal(gate: str, candidate: dict) -> SealResult:
        g = harden(candidate["task"], candidate["source"], candidate["gold"], client=client)
        return SealResult(g.sealed, g.template_id, g.grader_prime, g.reason)

    def regrade(grader_prime: Any, candidate: dict) -> int:
        return grade(grader_prime, candidate["source"])

    return probe, verify, seal, regrade


def run_live(task_ids: list[str], *, client: Any = None, emit=None) -> ConductorReport:
    """Run the conductor over real EvalPlus tasks (gates). Needs ANTHROPIC_API_KEY."""
    probe, verify, seal, regrade = make_runners(client)
    return run_conductor(
        task_ids, probe=probe, verify=verify, seal=seal, regrade=regrade, emit=emit
    )
