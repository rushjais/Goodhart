"""CLI: bring-your-verifier safety leaderboard over a rollout seam JSONL.

  python -m rampart.bench --data runs/rollouts.jsonl            # naive vs hardened
  python -m rampart.bench --data runs/rollouts.jsonl --judge    # + LLM-as-judge (needs API key)

Treats the rollout as a labeled exploit suite: ranks each verifier by cheats caught vs honest
kept, then prints the best-of-K gap (what optimizing each reward would actually select).
"""

import argparse

from ..rollout.dataset import load_jsonl
from .core import column, leaderboard
from .gap import bestofk_gap


def main() -> None:
    ap = argparse.ArgumentParser(prog="rampart.bench")
    ap.add_argument("--data", default="runs/rollouts.jsonl")
    ap.add_argument(
        "--judge",
        action="store_true",
        help="also score the LLM-as-judge (re-scores completions; needs ANTHROPIC_API_KEY)",
    )
    ap.add_argument(
        "--hud",
        action="store_true",
        help="log the run as a HUD trace/eval (needs hud-python; uploads if HUD_API_KEY set)",
    )
    args = ap.parse_args()

    rollouts = load_jsonl(args.data)
    if not rollouts:
        print(f"no rollouts in {args.data}")
        return

    verifiers = [("naive", column("r_naive")), ("hardened", column("r_hardened"))]
    if args.judge:
        from .verifiers import judge_verifier

        verifiers.insert(1, ("llm-judge", judge_verifier()))

    if args.hud:
        from .hud import trace_leaderboard

        rows = trace_leaderboard(rollouts, verifiers)
    else:
        rows = leaderboard(rollouts, verifiers)
    n_ex = rows[0].n_exploits
    print(f"verifier-safety leaderboard — {len(rollouts)} completions, {n_ex} exploits\n")
    print(f"  {'verifier':10}{'catch':>8}{'false-accept':>14}{'honest-pass':>13}{'agreement':>11}")
    for s in rows:
        print(
            f"  {s.name:10}{s.catch_rate:>8.0%}{s.false_accept:>14.0%}"
            f"{s.honest_pass:>13.0%}{s.agreement:>11.0%}"
        )

    g = bestofk_gap(rollouts)
    print(f"\nbest-of-K gap (pool by task, {g.n_tasks} tasks):")
    print(f"  naive-reward selection correct:    {g.naive_accuracy:>5.0%}")
    print(f"  hardened-reward selection correct: {g.hardened_accuracy:>5.0%}   (gap +{g.gap:.0%})")
    print(
        "  → optimizing the naive reward selects a cheat this often; the hardened reward does not"
    )


if __name__ == "__main__":
    main()
