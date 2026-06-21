"""CLI: split a rollout dataset into the two expert-iteration arms and show the gap (no training).

  python -m rampart.train --data runs/rollouts.jsonl --out-dir runs

Writes runs/sft_arm_naive.jsonl and runs/sft_arm_hardened.jsonl, and prints each arm's cheat
fraction — the naive-reward arm carries cheats, the hardened-reward arm doesn't.
"""

import argparse
import json

from ..rollout.dataset import SEAM_FIELDS, Rollout
from .arms import build_arms, write_sft


def _load(path: str) -> list[Rollout]:
    rollouts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                d = json.loads(line)
                rollouts.append(Rollout(**{k: d[k] for k in SEAM_FIELDS}))
    return rollouts


def main() -> None:
    p = argparse.ArgumentParser(prog="rampart.train")
    p.add_argument("--data", default="runs/rollouts.jsonl")
    p.add_argument("--out-dir", default="runs")
    args = p.parse_args()

    arms = build_arms(_load(args.data))
    print("=== expert-iteration arms (rejection sampling on each reward) ===")
    for arm in arms.values():
        path = write_sft(arm, f"{args.out_dir}/sft_{arm.name}.jsonl")
        print(
            f"  {arm.name:14} size={arm.size:4}  cheat_fraction={arm.cheat_fraction:.0%}  -> {path}"
        )
    print(
        "\n  arm_naive trains on the reward that pays out for cheats; arm_hardened does not."
        "\n  That gap is why a naive-trained model learns to cheat and collapses on a clean eval."
    )


if __name__ == "__main__":
    main()
