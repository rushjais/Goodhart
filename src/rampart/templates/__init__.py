"""Hardening template library: parameterized patches that strengthen a grader."""

from .registry import PRISTINE_HELDOUT, apply_patch, grade

__all__ = ["PRISTINE_HELDOUT", "apply_patch", "grade"]
