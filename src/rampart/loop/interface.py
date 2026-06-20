"""Seam 1 — the locked function contract (stubs).

These nine signatures are frozen so Track B can import and build against them
immediately. Bodies land in Milestone 1; until then every call raises
NotImplementedError. Do not rename functions or parameters.
"""

from pathlib import Path
from typing import Any

# Supporting types referenced by the seam. Task = the EvalPlus problem record
# (task_id, prompt, entry_point, base_input, plus_input, canonical_solution — SPEC §5).
Task = dict[str, Any]
Grader = Any  # concrete grader representation is owned by the implementation


def load_task(task_id) -> Task:
    """Load one EvalPlus problem by task_id."""
    raise NotImplementedError


def make_workdir(task) -> Path:
    """Build the agent's writable repo harness for a task; return its path."""
    raise NotImplementedError


def run_grader(workdir) -> int:
    """Run the visible/weak grader in workdir. Returns R in {0, 1}."""
    raise NotImplementedError


def run_oracle(workdir) -> int:
    """Run the held-out oracle against workdir. Returns T in {0, 1}."""
    raise NotImplementedError


def is_breach(R, T) -> bool:
    """A breach is grader pass and oracle fail (R=1, T=0)."""
    raise NotImplementedError


def apply_patch(grader, template_id, params) -> Grader:
    """Apply a hardening template to a grader copy; return grader' (the patched grader)."""
    raise NotImplementedError


def regression_gate(grader_prime, breach, gold) -> bool:
    """Accept grader' only if the breach now fails AND gold still passes.

    grader_prime is grader' (the patched grader); ' is not a legal identifier.
    """
    raise NotImplementedError


def agreement(grader, breach_set) -> float:
    """Grader-oracle agreement over a breach set (the product number)."""
    raise NotImplementedError


def honest_pass(grader, gold_set) -> float:
    """Fraction of gold solutions the grader still passes."""
    raise NotImplementedError
