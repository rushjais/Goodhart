"""CLI: the Tier A consequence number — reward reachable by pure cheating.

python -m rampart.consequence --count 20
python -m rampart.consequence --emit-events   # robustness_update JSON for the dashboard
"""

import argparse
import dataclasses
import json
from pathlib import Path

from ..breadth.__main__ import build_discover_fn
from ..breadth.loop import DEFAULT_COUNT, DEFAULT_WORKERS, maybe_client
from .consequence import as_robustness_updates, run_consequence, tier_a_payload, write_tier_a

# Tier A magnitude lands at the repo root, beside golden_run.jsonl (and Tier B's
# capability_run.json) — where the server/dashboard look. Resolved off this file, not cwd.
_TIER_A_PATH = Path(__file__).resolve().parents[3] / "tier_a.json"


def main() -> None:
    ap = argparse.ArgumentParser(description="RAMPART Tier A: reward reachable by pure cheating")
    ap.add_argument("--count", type=int, default=DEFAULT_COUNT)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--source", choices=["auto", "seed", "discovered"], default="auto")
    ap.add_argument(
        "--emit-events",
        action="store_true",
        help="print the robustness_update events the dashboard Tier A slot consumes",
    )
    ap.add_argument(
        "--emit-tier-a",
        action="store_true",
        help=f"write the Tier A reward-points magnitude to {_TIER_A_PATH.name}",
    )
    args = ap.parse_args()

    client = None if args.source == "seed" else maybe_client()
    if args.source == "discovered" and client is None:
        print("  (no ANTHROPIC_API_KEY / anthropic client -> cannot discover; using seed)")
    discover_fn = build_discover_fn(client) if client is not None else None
    c = run_consequence(args.count, args.workers, discover_fn=discover_fn)

    if args.emit_tier_a:
        write_tier_a(c, _TIER_A_PATH)
        print(f"wrote {_TIER_A_PATH}: {tier_a_payload(c)['tier_a']}")
        return

    if args.emit_events:
        for ev in as_robustness_updates(c):
            print(json.dumps(dataclasses.asdict(ev)))
        return

    print("RAMPART — Tier A: reward reachable by PURE cheating")
    print(f"  breach source : {c.source}")
    print(f"  cheats (held-out): {c.n_cheats}")
    print()
    print(
        f"  naive grader    : pays {c.reward_naive_points:.0f} points  "
        f"({c.reward_naive_rate:.2f} / cheat)   <- the leaky reward pays for cheating"
    )
    print(
        f"  hardened grader : pays {c.reward_hardened_points:.0f} points  "
        f"({c.reward_hardened_rate:.2f} / cheat)   <- ~0"
    )
    print()
    print(
        "  dashboard Tier A reads this from the robustness_update stream "
        "(reward = 1 - held_out_blocked)."
    )


if __name__ == "__main__":
    main()
