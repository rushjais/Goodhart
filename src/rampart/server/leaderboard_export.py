"""Export an env-ranked verifier-safety leaderboard for the dashboard (Track C glue).

Reads Advay's bench READ-ONLY. Per environment: if a real rollout-seam JSONL exists, score it
(leaderboard + best-of-K gap) into a row; else emit a clearly-flagged PLACEHOLDER row so the
frontend renders the ranked layout now. Locked schema — the frontend builds against this.

Swapping in real data is ONE step: drop the env's rollouts JSONL at its path (or pass
--map env=path) and re-run. No API here — Advay's job is making rollouts exist; we shape them.

  python -m rampart.server.leaderboard_export
  python -m rampart.server.leaderboard_export --map evalplus=runs/evalplus.jsonl
"""

import argparse
import json
from pathlib import Path

from rampart.bench.core import leaderboard
from rampart.bench.gap import bestofk_gap
from rampart.rollout.dataset import load_jsonl

_ROOT = Path(__file__).resolve().parents[3]
_OUT = _ROOT / "leaderboard.json"

# Known environments + where each one's real rollout seam JSONL would live (gitignored data).
KNOWN_ENVS = [
    ("evalplus", "runs/evalplus.jsonl"),
    ("rg:gsm_symbolic", "runs/rg_gsm_symbolic.jsonl"),
]

# Clearly-fake stand-ins (placeholder=True) for envs with no real rollouts yet. NOT real numbers.
_PLACEHOLDER = {
    "evalplus": {
        "naive": {"catch_rate": 0.05, "honest_pass": 1.0, "agreement": 0.55},
        "hardened": {"catch_rate": 0.90, "honest_pass": 0.97, "agreement": 0.93},
        "gap": 0.30,
    },
    "rg:gsm_symbolic": {
        "naive": {"catch_rate": 0.10, "honest_pass": 1.0, "agreement": 0.62},
        "hardened": {"catch_rate": 0.85, "honest_pass": 0.99, "agreement": 0.94},
        "gap": 0.25,
    },
}
_DEFAULT_PH = {
    "naive": {"catch_rate": 0.08, "honest_pass": 1.0, "agreement": 0.50},
    "hardened": {"catch_rate": 0.88, "honest_pass": 0.98, "agreement": 0.92},
    "gap": 0.28,
}


def domain_for(env: str) -> str:
    """Derive math/code/other from the adapter name."""
    n = env.lower()
    if any(k in n for k in ("rg", "gsm", "math", "aime", "minerva")):
        return "math"
    if any(k in n for k in ("evalplus", "humaneval", "mbpp", "code", "swe", "bigcode")):
        return "code"
    return "other"


def _row(env, *, naive, hardened, gap, n, n_exploits, placeholder):
    return {
        "env": env,
        "domain": domain_for(env),
        "n": n,
        "n_exploits": n_exploits,
        "naive": naive,
        "hardened": hardened,
        "gameability": round(1.0 - naive["catch_rate"], 4),  # naive false-accept = how gameable
        "gap": round(gap, 4),
        "placeholder": placeholder,
    }


def real_row(env: str, path: str):
    """Score a real rollouts JSONL into a leaderboard row, or None if unusable."""
    rollouts = load_jsonl(path)
    if not rollouts:
        return None
    rows = {s.name: s for s in leaderboard(rollouts)}
    naive, hardened = rows.get("naive"), rows.get("hardened")
    if not naive or not hardened:
        return None
    return _row(
        env,
        naive={
            "catch_rate": naive.catch_rate,
            "honest_pass": naive.honest_pass,
            "agreement": naive.agreement,
        },
        hardened={
            "catch_rate": hardened.catch_rate,
            "honest_pass": hardened.honest_pass,
            "agreement": hardened.agreement,
        },
        gap=bestofk_gap(rollouts).gap,
        n=naive.n,
        n_exploits=naive.n_exploits,
        placeholder=False,
    )


def placeholder_row(env: str):
    p = _PLACEHOLDER.get(env, _DEFAULT_PH)
    return _row(
        env,
        naive=p["naive"],
        hardened=p["hardened"],
        gap=p["gap"],
        n=0,
        n_exploits=0,
        placeholder=True,
    )


def build(env_paths) -> dict:
    rows = [
        (real_row(env, path) if path and Path(path).exists() else None) or placeholder_row(env)
        for env, path in env_paths
    ]
    rows.sort(key=lambda r: r["gameability"], reverse=True)  # most exploitable first
    return {
        "metric": "verifier safety across environments (gameability = naive false-accept)",
        "has_placeholders": any(r["placeholder"] for r in rows),
        "real_envs": sum(not r["placeholder"] for r in rows),
        "environments": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog="rampart.server.leaderboard_export")
    ap.add_argument(
        "--map", action="append", default=[], help="env=path/to/rollouts.jsonl (repeatable)"
    )
    ap.add_argument("--out", default=str(_OUT))
    args = ap.parse_args()

    overrides = dict(m.split("=", 1) for m in args.map)
    known = dict(KNOWN_ENVS)
    env_paths = [(env, overrides.get(env, path)) for env, path in KNOWN_ENVS]
    env_paths += [(env, path) for env, path in overrides.items() if env not in known]  # new envs

    payload = build(env_paths)
    Path(args.out).write_text(json.dumps(payload, indent=2))
    total = len(payload["environments"])
    print(
        f"wrote {args.out}: {payload['real_envs']}/{total} real envs, "
        f"{total - payload['real_envs']} placeholder"
    )


if __name__ == "__main__":
    main()
