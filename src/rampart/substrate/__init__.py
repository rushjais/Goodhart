"""Substrate: load EvalPlus problems and derive expected outputs from the gold."""

from .evalplus_task import Task, expected_outputs, load_task

__all__ = ["Task", "expected_outputs", "load_task"]
