"""Rollout layer: sample a policy against the task, score every rollout under naive reward,
hardened reward, and the oracle → the comprehensive RL dataset + the consequence number."""

from .dataset import Rollout, RolloutReport, generate_rollouts, score_completion, write_jsonl
from .policy import make_policy

__all__ = [
    "Rollout",
    "RolloutReport",
    "generate_rollouts",
    "make_policy",
    "score_completion",
    "write_jsonl",
]
