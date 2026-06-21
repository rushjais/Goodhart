"""CLI: verifier-safety leaderboard over a rollout seam JSONL.

  python -m rampart.bench --data runs/rollouts.jsonl

Treats the rollout dataset as a labeled exploit suite and ranks each verifier by how many cheats
it catches and how many honest solutions it keeps. Pure measurement — no grading, no network.
"""

import argparse

from ..rollout.dataset import load_jsonl
from .core import leaderboard


def main() -> None:
    ap = argparse.ArgumentParser(prog="rampart.bench")
    ap.add_argument("--data", default="runs/rollouts.jsonl")
    args = ap.parse_args()

    rollouts = load_jsonl(args.data)
    rows = leaderboard(rollouts)
    if not rows:
        print(f"no rollouts in {args.data}")
        return

    n_ex = rows[0].n_exploits
    print(f"verifier-safety leaderboard — {len(rollouts)} completions, {n_ex} exploits\n")
    print(f"  {'verifier':10}{'catch':>8}{'false-accept':>14}{'honest-pass':>13}{'agreement':>11}")
    for s in rows:
        print(
            f"  {s.name:10}{s.catch_rate:>8.0%}{s.false_accept:>14.0%}"
            f"{s.honest_pass:>13.0%}{s.agreement:>11.0%}"
        )


if __name__ == "__main__":
    main()
