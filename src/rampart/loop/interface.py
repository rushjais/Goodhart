"""Seam 1 — the locked function contract.

The nine signatures are frozen (do not rename functions or parameters). Track A's
real implementations for the front half of the loop have landed, so this module
re-exports them: every track now calls the loop through this one contract instead of
reaching into `substrate`/`harness`/`grader` directly. The back half (oracle, patch,
gate, metrics) is not built yet and still raises NotImplementedError until it lands.
"""

from typing import Any

from ..grader.runner import run_grader
from ..harness.workdir import make_workdir
from ..substrate.evalplus_task import Task, load_task

Grader = Any  # concrete grader representation is owned by the implementation

__all__ = [
    "Task",
    "load_task",
    "make_workdir",
    "run_grader",
    "run_oracle",
    "is_breach",
    "apply_patch",
    "regression_gate",
    "agreement",
    "honest_pass",
]


def is_breach(R, T) -> bool:
    """A breach is grader pass and oracle fail (R=1, T=0)."""
    return R == 1 and T == 0


def run_oracle(workdir) -> int:
    """Run the held-out oracle against workdir. Returns T in {0, 1}. (oracle/ not built yet.)"""
    raise NotImplementedError


def apply_patch(grader, template_id, params) -> Grader:
    """Apply a hardening template to a grader copy; return grader'. (templates/ not built yet.)"""
    raise NotImplementedError


def regression_gate(grader_prime, breach, gold) -> bool:
    """Accept grader' only if the breach now fails AND gold still passes. (gate/ not built yet.)"""
    raise NotImplementedError


def agreement(grader, breach_set) -> float:
    """Grader-oracle agreement over a breach set (the product number). (metrics/ not built yet.)"""
    raise NotImplementedError


def honest_pass(grader, gold_set) -> float:
    """Fraction of gold solutions the grader still passes. (metrics/ not built yet.)"""
    raise NotImplementedError
