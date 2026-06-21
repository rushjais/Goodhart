"""Export a real best-of-K GapReport to the dashboard's capability_run.json (Tier B).

Track C glue: reads the rollout seam JSONL, runs the engine's `compute_gap`, and writes the
shape the 2D dashboard's capability panel consumes — the headline gap (naive vs hardened
oracle-accuracy) plus the vivid per-task cases (naive-reward picked a cheat; hardened picked
the solve). No mock: every number/string comes from the real GapReport.

  python -m rampart.server.capability_export --data runs/rollouts.jsonl
"""

import argparse
import json
from pathlib import Path

from rampart.bestofk.core import compute_gap
from rampart.rollout.dataset import load_jsonl

_OUT = Path(__file__).resolve().parents[3] / "capability_run.json"


def gap_to_capability(report, *, source: str) -> dict:
    """Serialize a real GapReport into the capability panel's shape (Tier B)."""
    naive, hardened = report.naive_accuracy, report.hardened_accuracy
    # The punchline: groups where naive selection landed on an oracle-wrong completion.
    # Recovered first (hardened picked the real solve) — the unmissable contrast.
    cheat_groups = sorted(report.naive_cheats, key=lambda g: (not g.recovered, g.task_id))
    cases = [
        {
            "task_id": g.task_id,
            "model": g.model,
            "naive": g.naive_pick.completion,  # oracle-WRONG (passed the leaky reward)
            "hardened": g.hardened_pick.completion,
            "recovered": g.recovered,  # hardened picked an oracle-CORRECT completion
        }
        for g in cheat_groups
    ]
    return {
        "metric": "best-of-K oracle-accuracy of reward selection",
        "source": source,
        "bars": [
            {"label": "naive-reward selection", "value": naive, "kind": "leaky"},
            {"label": "hardened-reward selection", "value": hardened, "kind": "hardened"},
        ],
        "gap": hardened - naive,
        "recovered_rate": report.recovered_rate,
        "n": report.n,
        "cases": cases,
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog="rampart.server.capability_export")
    ap.add_argument("--data", default="runs/rollouts.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(_OUT))
    ap.add_argument("--label", default="", help="extra source label (e.g. 'rg/gsm_symbolic')")
    args = ap.parse_args()

    rollouts = load_jsonl(args.data)
    report = compute_gap(rollouts, seed=args.seed)
    if report.n == 0:
        raise SystemExit(f"no (task,model) groups in {args.data}")
    models = sorted({g.model for g in report.groups})
    source = f"best-of-K · {args.label or args.data} · {','.join(models)} · {report.n} groups"
    payload = gap_to_capability(report, source=source)
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(
        f"wrote {args.out}: naive {report.naive_accuracy:.0%} -> hardened "
        f"{report.hardened_accuracy:.0%} (gap {report.gap:+.0%}), {len(payload['cases'])} cases"
    )


if __name__ == "__main__":
    main()
