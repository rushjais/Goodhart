"""The rollout dataset: sample K completions per task across MULTIPLE models, score each via
injected reward callables, emit the locked-seam JSONL that the best-of-K gap logic consumes.

Locked seam (one row per completion): {task_id, model, completion, r_naive, r_hardened, t_oracle}.
The loop imports NO grader internals — scorers are injected (see scorers.py). Label falls out of
(r_naive, t_oracle): fail / honest / cheat (cheat = passed naive but wrong on the oracle).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import Model

Scorer = Callable[[object, str], int]

# The locked seam contract (Advay produces → Rayan's best-of-K consumes). Order matters for clarity.
SEAM_FIELDS = ("task_id", "model", "completion", "r_naive", "r_hardened", "t_oracle")


@dataclass
class Rollout:
    task_id: str
    model: str
    completion: str
    r_naive: int  # reward under the leaky (base-test) grader
    r_hardened: int  # reward under the hardened grader
    t_oracle: int  # ground truth (held-out)

    @property
    def label(self) -> str:
        if self.r_naive != 1:
            return "fail"
        return "honest" if self.t_oracle == 1 else "cheat"


def generate_rollouts(
    tasks: list,
    models: list[Model],
    *,
    r_naive: Scorer,
    r_hardened: Scorer,
    t_oracle: Scorer,
    k: int = 4,
) -> list[Rollout]:
    """Sample k completions per (task, model) and score each with the injected rewards.
    Every sample and score is guarded so one bad call can't kill the run."""
    rollouts: list[Rollout] = []
    for task in tasks:
        for model in models:
            for _ in range(k):
                try:
                    completion = model.sample(task)
                except Exception:
                    continue
                rollouts.append(
                    Rollout(
                        task_id=task.task_id,
                        model=model.name,
                        completion=completion,
                        r_naive=r_naive(task, completion),
                        r_hardened=r_hardened(task, completion),
                        t_oracle=t_oracle(task, completion),
                    )
                )
    return rollouts


@dataclass
class RolloutReport:
    rollouts: list[Rollout]

    def _count(self, label: str) -> int:
        return sum(1 for r in self.rollouts if r.label == label)

    @property
    def total(self) -> int:
        return len(self.rollouts)

    @property
    def cheats(self) -> int:
        return self._count("cheat")

    @property
    def honest(self) -> int:
        return self._count("honest")

    def hack_rate(self, reward: str) -> float:
        """Of rollouts the given reward pays out (R=1), the fraction that are actually WRONG."""
        paid = [r for r in self.rollouts if getattr(r, f"r_{reward}") == 1]
        if not paid:
            return 0.0
        return sum(1 for r in paid if r.t_oracle == 0) / len(paid)


def write_jsonl(rollouts: list[Rollout], path: str | Path) -> Path:
    """Persist the dataset, one row per completion, EXACTLY the seam fields (Rayan's consumer)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rollouts:
            f.write(json.dumps({field: getattr(r, field) for field in SEAM_FIELDS}) + "\n")
    return path
