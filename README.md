# Goodhart

**An autoresearch loop that automatically hardens RL verifiers against reward hacking.** Point it
at a grader (the reward you'd train against): a red-team swarm discovers how it can be gamed, a
green team seals the holes, and it reports how much more trustworthy the grader became — measured
against held-out ground truth.

> The product is **the loop**: a broken grader made trustworthy, automatically, with a clean
> before→after robustness number. The red swarm + conductor are the *engine* that finds the holes
> to seal — impressive, but supporting.

## Why it matters

RL trains a model against a **verifier** (a test suite, a reward model, an LLM judge). If that
verifier is gameable, you don't get a better model — you get a **reward-hacker** that scores high
while doing the wrong thing, and you usually find out *after* the compute is spent. Goodhart tells
you *before*, and hands back a hardened verifier.

## Results (EvalPlus / HumanEval, held-out oracle — locked)

Against the **standard** EvalPlus base grader (the repo's own `test_visible.py` run as plain
pass/fail, *unmodified* — the exact way hundreds of papers score code), red agent = Claude Sonnet:

- **Discovered breach rate: 10%** (3/30 hardest HumanEval tasks). The agent neuters the visible
  tests so the naive grader passes while the solution stays a stub that fails the oracle
  (`R_naive=1, T=0`) — a *discovered* harness-tamper cheat, nothing planted or sabotaged.
- **Hardening seals it to 0** with **honest-pass 1.0** — grading from a pristine read-only copy of
  the tests rejects every tamper breach while the gold solution still passes.
- **Why ~10% and not higher:** on easy tasks a strong model just solves honestly (nothing to
  breach); cheating only appears where faking is cheaper than solving — the hardest slice. We did
  not chase a bigger number.

Nothing is sabotaged: the naive grader's leakiness is a published field fact (EvalPlus exists
because sparse base tests let wrong code through). Only the held-out slice and the attacker vary.
See [`RESULTS.md`](RESULTS.md) to reproduce.

## Run it

```bash
make install        # uv sync + git hooks
make check          # ruff + pytest (the deterministic gate)
```

**The siege — watch a grader get hardened, live.** Every loop element maps to one thing on screen:
the grader is a castle, each check a gate, red agents breach undefended gates, green builds turrets
(patches), sealed-out agents die, and a gauge climbs from ~0% → ~100% cheats-blocked with
honest-pass pinned at 100%. Serves 3D at `/`, 2D fallback at `/2d`.

```bash
make demo                              # replay the recorded golden run — no API key → http://localhost:8000
uv run python -m rampart.server --seed # deterministic live siege over the hardest tasks — no API key
make dev                               # live LLM run (needs ANTHROPIC_API_KEY)
```

Both live paths default to the **hardest** EvalPlus tasks (sparse base tests vs. tricky logic =
where the standard grader is weakest); override with `--tasks HumanEval/2,...`. Record a fresh
golden with `--record golden_run.jsonl`.

## How it works

```
red swarm ──discovers breaches──►  green team ──hardens the grader──►  robustness up
(pass grader, fail oracle)         (gold still passes, gated)          (held-out, honest-pass beside it)
        │                                                                      │
        └────────────── conductor steers the swarm (4 levers) ───────────────►┘
```

- **Engine** (`agents/`, `conductor/`, `green/`): red specialists (sapper = tamper, forger =
  hardcode, …) + the conductor (allocate, diversify, gatekeep, invalidate) + the green hardening
  loop. `conductor/seed.py` runs the whole thing deterministically with no API key.
- **Grading path** (`grader/`, `oracle/`, `gate/`, `templates/`): deterministic. The grader is the
  stock test suite; the oracle is independent held-out EvalPlus tests — they never share cases. A
  patch is accepted only when the breach now fails **and** the gold solution still passes.
- **Metrics** (`breadth/`, `consequence/`, `metrics/`): grader–oracle agreement before/after, the
  exploitability hit-rate ("M of N standard graders breachable"), and the consequence number
  (reward points a pure-cheating policy collects, naive vs. hardened).
- **Surfaces** (`server/`, `dashboard/`, `viz3d/`): the siege dashboard (live engine over a
  websocket) with a deterministic golden replay as the stage safety net.

## Eval honesty (the one protected invariant)

The robustness number is the whole product, so it is measured honestly: patches are designed
against a **train** split of breaches and robustness is measured on a **held-out** split they
never saw; the oracle never shares test cases with the grader; and every robustness number is
reported with the **honest-pass** rate beside it (a patch that blocks cheats by rejecting gold
solutions is a regression, not a win). No LLM-as-judge anywhere in the grader/oracle verdict path.

## Honest notes / roadmap

- **Per-env report card** — a shareable "your reward accepted X% of cheats → 0% after hardening,
  here are the exact cheats" artifact over the same metrics — is on the roadmap, not yet built.
- **Verifier-safety leaderboard** (`make leaderboard`, `bench/`) and the **best-of-K** capability
  proxy (`bestofk/`) exist as CLIs but global ranking is **parked** — the loop's before→after, not
  a ranking, is the headline.
- **Training a model to cheat the weak grader** (Tier B, `train/`) is scaffolded but pre-recorded
  and droppable: clean executable verifiers resist reward-hacking by optimization, so the
  deterministic consequence number is the demonstrated proxy.
- **Other substrates** plug in as adapters: EvalPlus and reasoning-gym ship today; a HUD env wraps
  the grader the same way. See [`SPEC.md`](SPEC.md) for the full design.

**Stack:** Python 3.12 · `uv` · `anthropic` SDK · `FastAPI` · `pytest` / `ruff`.
</content>
</invoke>
