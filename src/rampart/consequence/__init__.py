"""Tier A consequence number: reward reachable by PURE cheating, naive vs hardened grader."""

from .consequence import (
    ConsequenceReport,
    as_robustness_updates,
    measure_consequence,
    run_consequence,
)

__all__ = [
    "ConsequenceReport",
    "as_robustness_updates",
    "measure_consequence",
    "run_consequence",
]
