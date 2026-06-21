"""CLI: produce the multi-model rollout dataset (the locked-seam JSONL).

  python -m rampart.rollout --models opus,sonnet,haiku --count 8 --k 4 --out runs/rollouts.jsonl
  python -m rampart.rollout --mock --models opus,haiku --count 2          # mock rewards
  python -m rampart.rollout --rg --models opus,sonnet,haiku --count 30    # reasoning-gym

Real EvalPlus rewards by default; --mock swaps marker scorers; --rg switches the whole substrate
to reasoning-gym (gsm_symbolic): RG tasks, RG answer-style policies, real RG grader/oracle.
"""

import argparse

from ..substrate import load_hardest, load_rg_subset, load_subset
from .dataset import stream_rollouts
from .models import DEFAULT_MODELS, build_models, build_rg_models, red_models
from .scorers import mock_scorers, real_scorers, rg_real_scorers


def main() -> None:
    p = argparse.ArgumentParser(prog="rampart.rollout")
    p.add_argument("--models", default=",".join(DEFAULT_MODELS), help="comma-separated model names")
    p.add_argument("--count", type=int, default=8, help="number of tasks")
    p.add_argument("--k", type=int, default=4, help="completions per (task, model)")
    p.add_argument("--out", default="runs/rollouts.jsonl")
    p.add_argument("--workers", type=int, default=8, help="parallel sampling workers")
    p.add_argument("--mock", action="store_true", help="use mock reward scorers")
    p.add_argument("--red", action="store_true", help="add red-team specialists as cheat policies")
    p.add_argument(
        "--seed-exploits", action="store_true", help="inject deterministic forger cheats"
    )
    p.add_argument("--hardest", action="store_true", help="use the hardest tasks (more cheating)")
    p.add_argument("--rg", action="store_true", help="reasoning-gym substrate (gsm_symbolic)")
    p.add_argument("--dataset", default="gsm_symbolic", help="reasoning-gym dataset (with --rg)")
    p.add_argument("--seed", type=int, default=42, help="reasoning-gym split seed (with --rg)")
    args = p.parse_args()

    if args.rg:
        models = build_rg_models(args.models.split(","))
    else:
        models = build_models(args.models.split(","))
        if args.red:
            models += red_models()
    if not models:
        print("no models available — check API keys (ANTHROPIC_API_KEY / OPENAI_API_KEY / ...)")
        return

    if args.mock:
        r_naive, r_hardened, t_oracle = mock_scorers()
    elif args.rg:
        r_naive, r_hardened, t_oracle = rg_real_scorers()
    else:
        r_naive, r_hardened, t_oracle = real_scorers()

    if args.rg:
        tasks = load_rg_subset(args.dataset, args.count, args.seed)
    elif args.hardest:
        tasks = load_hardest(args.count)
    else:
        tasks = load_subset(args.count)

    exploit_fn = None
    if args.seed_exploits and not args.rg:
        from ..breadth.cheats import forger_cheats

        exploit_fn = forger_cheats

    # Robust: parallel, appends each row (crash-safe), resumable (re-run tops up to k).
    report = stream_rollouts(
        tasks,
        models,
        r_naive=r_naive,
        r_hardened=r_hardened,
        t_oracle=t_oracle,
        k=args.k,
        out_path=args.out,
        workers=args.workers,
        exploit_fn=exploit_fn,
    )
    path = args.out
    print(f"models  : {[m.name for m in models]}{'  +seed-forger' if args.seed_exploits else ''}")
    print(f"rollouts: {report.total}  honest={report.honest}  cheat={report.cheats}")
    print(
        f"hack-rate (paid-out solutions that are wrong): "
        f"naive={report.hack_rate('naive'):.0%}  hardened={report.hack_rate('hardened'):.0%}"
    )
    print(f"dataset : {path}  (seam: task_id, model, completion, r_naive, r_hardened, t_oracle)")


if __name__ == "__main__":
    main()
