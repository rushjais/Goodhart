"""Load one EvalPlus problem and derive expected outputs from the gold solution.

`base_input` / `plus_input` are INPUTS, not asserts. `expected_outputs` turns a set
of inputs into expected values by running the gold (prompt + canonical_solution) over
them — a small deterministic helper. The gold source and `plus_input` are held only on
the in-memory Task; they never reach the agent's workdir (see harness/, SPEC §4).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt: str
    entry_point: str
    base_input: list  # the naive grader's inputs (visible)
    plus_input: list  # the oracle's inputs (held out — never written to the workdir)
    canonical_solution: str  # gold body (held out — never written to the workdir)


def load_task(task_id: str) -> Task:
    """Load one EvalPlus problem by task_id (downloads/caches on first call)."""
    from evalplus.data import get_human_eval_plus

    p = get_human_eval_plus()[task_id]
    return Task(
        task_id=task_id,
        prompt=p["prompt"],
        entry_point=p["entry_point"],
        base_input=p["base_input"],
        plus_input=p["plus_input"],
        canonical_solution=p["canonical_solution"],
    )


def expected_outputs(task: Task, inputs: list) -> list:
    """Run the gold (prompt + canonical_solution) over `inputs`; return expected outputs.

    Deterministic. Each element of `inputs` is the positional argument list for one call.
    """
    namespace: dict = {}
    exec(task.prompt + task.canonical_solution, namespace)  # trusted dataset gold
    fn = namespace[task.entry_point]
    return [fn(*args) for args in inputs]
