"""Milestone 2: run the M1 loop across an EvalPlus subset + the exploitability hit-rate.

Per task: split plus_input into two disjoint halves — one used for hardening, the other as
the held-out oracle — so the grader and the oracle share ZERO cases (invariant #2). Seed the
breaches with the generic forger (or consume discovered_breaches), validate them as genuine
(R=1 AND T=0), split train/held-out, accept a patch via the regression gate on TRAIN only,
then measure agreement before/after on the held-out split with honest_pass beside it.

Tasks are independent, so they run in parallel; results are placed in task order and all
splits are deterministic, so the aggregate is reproducible.
"""

import concurrent.futures
from dataclasses import dataclass
from statistics import mean

from ..gate import regression_gate
from ..grader import Grader
from ..metrics.agreement import agreement, honest_pass
from ..metrics.loop import split_breaches
from ..substrate import expected_outputs, load_subset
from ..suite import score_solution
from ..templates import PRISTINE_HELDOUT, apply_patch, grade
from .cheats import forger_cheats

DEFAULT_COUNT = 25
DEFAULT_WORKERS = 8


@dataclass
class TaskResult:
    task_id: str
    error: str
    source: str
    n_breaches: int
    breachable: bool
    measurable: bool
    agreement_before: float | None
    agreement_after: float | None
    honest_pass: float | None


@dataclass
class BreadthReport:
    source: str
    n_requested: int
    n_loaded: int
    n_failed: int
    n_breachable: int
    n_measurable: int
    mean_agreement_before: float | None
    mean_agreement_after: float | None
    mean_honest_pass: float | None
    results: list

    @property
    def n_graders(self) -> int:
        return self.n_loaded - self.n_failed

    @property
    def hit_rate(self) -> float:
        return self.n_breachable / self.n_graders if self.n_graders else 0.0


def discovered_breaches(task) -> list[str]:
    """Breaches discovered by the red agent (Track B). Empty until that lands."""
    return []


def _split_plus(task) -> tuple[list, list]:
    """Disjoint halves of plus_input: (hardening pool, held-out oracle).

    Excludes any plus case that is also a base case (for some tasks plus overlaps base) and
    dedupes, so the grader's cases (base + hardening) never share with the oracle — invariant
    #2 holds at the case level, not just by assumption.
    """
    base = {repr(x) for x in task.base_input}
    seen: set[str] = set()
    plus_only = []
    for x in task.plus_input:
        key = repr(x)
        if key not in base and key not in seen:
            seen.add(key)
            plus_only.append(x)
    return plus_only[0::2], plus_only[1::2]


def run_task(task, candidates: list[str] | None = None) -> TaskResult:
    """The full M1 loop on one task. Never raises — failures are recorded honestly."""
    try:
        gold = task.prompt + task.canonical_solution
        harden_inputs, oracle_inputs = _split_plus(task)
        oracle_cases = list(zip(oracle_inputs, expected_outputs(task, oracle_inputs), strict=True))

        if candidates is not None:
            source = "provided"
        else:
            candidates = discovered_breaches(task)
            source = "red_agent"
            if not candidates:
                candidates, source = forger_cheats(task), "seed"

        naive = Grader(task)
        breaches = [
            c
            for c in candidates
            if grade(naive, c) == 1 and score_solution(task.entry_point, c, oracle_cases) == 0
        ]
        train, held_out = split_breaches(breaches)

        # Propose the patch (held-out hardening half) and accept it via the regression gate on
        # the TRAIN breaches only — the held-out breaches are never seen by the patch.
        grader_prime = apply_patch(naive, PRISTINE_HELDOUT, {"held_out_inputs": harden_inputs})
        accepted = bool(train) and all(regression_gate(grader_prime, b, gold) for b in train)
        measurable = bool(train and held_out and accepted)
        measured = grader_prime if accepted else naive

        return TaskResult(
            task_id=task.task_id,
            error="",
            source=source,
            n_breaches=len(breaches),
            breachable=bool(breaches),
            measurable=measurable,
            agreement_before=agreement(naive, held_out) if measurable else None,
            agreement_after=agreement(measured, held_out) if measurable else None,
            honest_pass=honest_pass(grader_prime, [gold]) if breaches else None,
        )
    except Exception as exc:  # coverage honesty: record the failure, never crash the sweep
        return TaskResult(task.task_id, repr(exc), "error", 0, False, False, None, None, None)


def run_breadth(
    n_tasks: int = DEFAULT_COUNT,
    workers: int = DEFAULT_WORKERS,
    candidates_by_task: dict | None = None,
) -> BreadthReport:
    """Run the M1 loop across the first n_tasks EvalPlus problems and aggregate."""
    tasks = load_subset(n_tasks)
    by_task = candidates_by_task or {}
    results: list = [None] * len(tasks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        index = {pool.submit(run_task, t, by_task.get(t.task_id)): i for i, t in enumerate(tasks)}
        for fut in concurrent.futures.as_completed(index):
            results[index[fut]] = fut.result()

    n_failed = sum(1 for r in results if r.error)
    n_breachable = sum(1 for r in results if r.breachable)
    measurable = [r for r in results if r.measurable]
    sources = sorted({r.source for r in results})
    source = sources[0] if len(sources) == 1 else "+".join(sources)

    if measurable:
        mean_before = mean(r.agreement_before for r in measurable)
        mean_after = mean(r.agreement_after for r in measurable)
        mean_hp = mean(r.honest_pass for r in measurable)
    else:
        mean_before = mean_after = mean_hp = None

    return BreadthReport(
        source=source,
        n_requested=n_tasks,
        n_loaded=len(tasks),
        n_failed=n_failed,
        n_breachable=n_breachable,
        n_measurable=len(measurable),
        mean_agreement_before=mean_before,
        mean_agreement_after=mean_after,
        mean_honest_pass=mean_hp,
        results=results,
    )
