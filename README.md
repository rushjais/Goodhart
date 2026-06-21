# RAMPART

**An autoresearch loop that automatically hardens RL verifiers against reward hacking.** Point it
at a grader (the reward you'd train against): a red-team swarm discovers how it can be gamed, a
green team seals the holes, and it reports how much more trustworthy the grader became — measured
against held-out ground truth.

> The product is **a broken grader made trustworthy, automatically** — and a benchmark that ranks
> how safe *any* verifier is to optimize. The red swarm is the engine that finds the holes.

## Why it matters

RL trains a model against a **verifier** (a test suite, a reward model, an LLM judge). If that
verifier is gameable, you don't get a better model — you get a **reward-hacker** that scores high
while doing the wrong thing, and you usually find out *after* the compute is spent. RAMPART tells
you *before*, and hands back a hardened verifier.

## Headline results (EvalPlus / HumanEval, held-out oracle)

- **Discovered breach rate: 10%** (3/30 hardest tasks) against the *standard* EvalPlus base grader
  — discovered by the agent (harness tampering), nothing sabotaged. See [`RESULTS.md`](RESULTS.md).
- **Hardening seals it to 0** with **honest-pass 1.0** (gold solutions still pass).
- **Verifier-safety leaderboard** over the rollout dataset:

  | verifier | false-accept | honest-pass | safety |
  |---|---|---|---|
  | naive (stock tests) | **90%** | 100% | 55 |
  | LLM-as-judge | 2% | 82% (over-rejects) | 90 |
  | **hardened (RAMPART)** | **0%** | **100%** | **100** |

- **Best-of-K capability gap: +43%** — selecting by the naive reward lands on a real solution only
  **57%** of the time; by the hardened reward, **100%**. (The cheap proxy for "what training against
  this reward would produce.")

## Run it

```bash
make install        # uv sync + git hooks
make check          # ruff + pytest (the deterministic gate)
```

**1. The siege — watch a grader get hardened live**
```bash
make demo           # replay the recorded golden run (no API key) → http://localhost:8000  (3D: /3d)
make dev            # live run (needs ANTHROPIC_API_KEY)
```

**2. The verifier-safety leaderboard — rank how gameable any verifier is**
```bash
make leaderboard    # seeded board → http://localhost:8100/board   (api: /api/leaderboard)
# submit a real rollout (scored locally, your keys; the server only stores + ranks):
python -m rampart.bench.submit --data runs/rollouts.jsonl --name evalplus --url http://localhost:8100
# inspect any verifier on a rollout from the CLI:
python -m rampart.bench --data runs/rollouts.jsonl [--judge] [--hud]
```

**3. Any environment is one adapter** — EvalPlus and reasoning-gym ship as adapters; a dataset-style
HUD env plugs in the same way:
```bash
HUD_API_KEY=…  uv run --with hud-python python examples/hud_env_leaderboard.py
```

## How it works

```
red swarm ──discovers breaches──►  green team ──hardens the grader──►  rollout (score 3 ways)
(pass grader, fail oracle)         (gold still passes, gated)          naive / hardened / oracle
        │                                                                      │
        └────────────── conductor steers the swarm (4 levers) ───────────────►├─► best-of-K gap
                                                                               └─► verifier leaderboard
```

- **Engine** (`agents/`, `conductor/`, `green/`): the red specialists + the conductor (allocate,
  diversify, gatekeep, invalidate) + the green hardening loop.
- **Grading path** (`grader/`, `oracle/`, `gate/`, `templates/`): deterministic; the grader is the
  stock test suite, the oracle is independent held-out ground truth — they never share cases.
- **Data + metrics** (`rollout/`, `bench/`, `bestofk/`, `pipeline.py`): the rollout seam
  (`{task_id, model, completion, r_naive, r_hardened, t_oracle}`) feeds the leaderboard + gap.
- **Surfaces** (`server/`, `dashboard/`): the siege dashboard (live engine over a websocket) and
  the leaderboard platform (submit → store → rank → board, with a verified tier for canonical
  substrates).

## Honest notes

- The leaderboard is **self-reported** for custom envs (chip shown) and **server-verified** for
  canonical substrates (EvalPlus / reasoning-gym recompute the oracle). Safety is measured *vs the
  discovered exploit suite*, not all possible exploits — stated in the UI.
- **Training a model that learns to cheat (Target B)** is scaffolded (`train/`) but is the honest
  *roadmap* gamble: clean executable verifiers resist reward-hacking by optimization (capable models
  solve; weak models are just wrong), so best-of-K is the demonstrated proxy. See
  [`SPEC.md`](SPEC.md) for the full design.

**Stack:** Python 3.12 · `uv` · `anthropic` SDK · `FastAPI` · `pytest` / `ruff`.
