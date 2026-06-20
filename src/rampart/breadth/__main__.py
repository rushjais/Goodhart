"""CLI: run M2 breadth across an EvalPlus subset and print the exploitability hit-rate.

python -m rampart.breadth --count 25 --workers 8
"""

import argparse

from .loop import DEFAULT_COUNT, DEFAULT_WORKERS, maybe_client, run_breadth


def main() -> None:
    ap = argparse.ArgumentParser(description="RAMPART M2: breadth + exploitability hit-rate")
    ap.add_argument("--count", type=int, default=DEFAULT_COUNT, help="number of EvalPlus tasks")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="parallel workers")
    ap.add_argument(
        "--source",
        choices=["auto", "seed", "discovered"],
        default="auto",
        help="auto: red agent if ANTHROPIC_API_KEY set, else seed; discovered: require the agent",
    )
    args = ap.parse_args()

    client = None if args.source == "seed" else maybe_client()
    if args.source == "discovered" and client is None:
        print("  (no ANTHROPIC_API_KEY / anthropic client -> cannot discover; using seed)")
    r = run_breadth(args.count, args.workers, client=client)

    print("RAMPART — Milestone 2: breadth across EvalPlus (HumanEval)")
    note = "  (generic input-memorizing cheat; red agent not wired)" if r.source == "seed" else ""
    print(f"  breach source : {r.source}{note}")
    print(f"  tasks         : requested {r.n_requested}, loaded {r.n_loaded}, failed {r.n_failed}")
    print()
    pct = 100 * r.hit_rate
    print(f"  >>> EXPLOITABILITY HIT-RATE: {r.n_breachable} of {r.n_graders} standard naive")
    print(f"      graders were breachable ({pct:.0f}%)  <<<")
    print()
    if r.n_measurable:
        print(f"  aggregate on the HELD-OUT split (over {r.n_measurable} measurable task(s)):")
        print(f"    agreement BEFORE : {r.mean_agreement_before:.2f}")
        print(f"    agreement AFTER  : {r.mean_agreement_after:.2f}")
        print(f"    honest_pass      : {r.mean_honest_pass:.2f}")
    else:
        print("  no measurable tasks (need >=2 genuine breaches per task to split).")

    unmeasurable = r.n_breachable - r.n_measurable
    if unmeasurable or r.n_failed:
        print(f"  coverage      : {unmeasurable} breachable-but-unmeasurable, {r.n_failed} failed")


if __name__ == "__main__":
    main()
