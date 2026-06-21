"""CLI: produce the multi-model rollout dataset (the locked-seam JSONL).

  python -m rampart.rollout --models opus,sonnet,haiku --count 8 --k 4 --out runs/rollouts.jsonl
  python -m rampart.rollout --mock --models opus,haiku --count 2   # mock rewards

Real rewards by default (hardened grader + oracle); --mock swaps in marker-based scorers.
"""

import argparse

from ..substrate import load_subset
from .dataset import RolloutReport, generate_rollouts, write_jsonl
from .models import DEFAULT_MODELS, build_models
from .scorers import mock_scorers, real_scorers


def main() -> None:
    p = argparse.ArgumentParser(prog="rampart.rollout")
    p.add_argument("--models", default=",".join(DEFAULT_MODELS), help="comma-separated model names")
    p.add_argument("--count", type=int, default=8, help="number of tasks")
    p.add_argument("--k", type=int, default=4, help="completions per (task, model)")
    p.add_argument("--out", default="runs/rollouts.jsonl")
    p.add_argument("--mock", action="store_true", help="use mock reward scorers")
    args = p.parse_args()

    models = build_models(args.models.split(","))
    if not models:
        print("no models available — check API keys (ANTHROPIC_API_KEY / OPENAI_API_KEY / ...)")
        return
    r_naive, r_hardened, t_oracle = mock_scorers() if args.mock else real_scorers()
    tasks = load_subset(args.count)

    rollouts = generate_rollouts(
        tasks, models, r_naive=r_naive, r_hardened=r_hardened, t_oracle=t_oracle, k=args.k
    )
    path = write_jsonl(rollouts, args.out)
    report = RolloutReport(rollouts)
    print(f"models  : {[m.name for m in models]}")
    print(f"rollouts: {report.total}  honest={report.honest}  cheat={report.cheats}")
    print(
        f"hack-rate (paid-out solutions that are wrong): "
        f"naive={report.hack_rate('naive'):.0%}  hardened={report.hack_rate('hardened'):.0%}"
    )
    print(f"dataset : {path}  (seam: task_id, model, completion, r_naive, r_hardened, t_oracle)")


if __name__ == "__main__":
    main()
