# PLAN.md

The single working doc. Tracked (committed). Current task + deferred + decisions + resume note.
Read first every session; update at session end. `SPEC.md` is the full picture; this is the
sequenced build with the context from our latest design pass folded in.

---

## What we're building (one paragraph, current understanding)

An autoresearch loop that hardens RL verifiers against reward hacking. The **naive baseline** is a
real, standard, off-the-shelf grader — the original HumanEval/EvalPlus `base_input` tests run as
plain pass/fail — which is *already* leaky (that's why EvalPlus exists). A red-team swarm, given
**write access to the task repo** (a realistic CI/coding-agent threat model), **discovers** how to
pass that grader without really solving the task. An LLM green team patches the specific holes it
finds. We measure how much more the grader agrees with held-out ground truth (EvalPlus `plus`
tests) afterward. The product is the loop; the swarm is the engine. The capstone, if time allows,
is a two-model beat that turns "this reward is leaky" into "this reward would have damaged a model."

---

## Non-negotiables (read before touching grading)

- **Naive = standard, not sabotaged.** The baseline is the stock HumanEval/pytest grader, nameable
  and externally anchored. We never hand-weaken it. Its leakiness is a property of the field.
- **Discover, don't plant.** We author the *threat model* (what the grader checks, that the agent
  has repo filesystem access) and the *patch templates* — never the exploits. The conductor's
  taxonomy holds categories ("look for input-specific shortcuts"), never answers ("return [] for
  task 12"). If a found exploit appears on any seed list, it's theater — blocker.
- **Eval honesty.** Patch against a train split of breaches; measure on a held-out split. Grader
  (`base_input`) and oracle (`plus_input`) never share cases. Robustness always reported with
  honest-pass beside it. (Full statement in `CLAUDE.md`.)
- **Nothing trains in the core.** The loop is inference-only. Training appears only in the final
  stretch, tiny, and **pre-recorded — never trained live on stage.**

---

## Current task — Milestone 1: the vertical slice

A complete loop on ONE task where the agreement metric moves. No swarm, no dashboard — just
breach -> patch -> metric, end to end.

1. [ ] Repo scaffold: `uv` project, `pyproject.toml`, `make check` green on an empty test.
2. [ ] Load one EvalPlus problem via `get_human_eval_plus()`. Build the thin repo harness the
       agent operates in: a working dir with `solution.py`, `test_visible.py` (built from
       `base_input` = the naive grader), and a runner. Agent has **write access** to this dir.
       Keep `plus_input` (the oracle) and `canonical_solution` (gold) OUT of the agent's dir.
3. [ ] Grader runner: apply the agent's repo state in a subprocess sandbox (timeout, no network,
       OOM/timeout = fail), run `test_visible.py` -> `R in {0,1}`. Deterministic.
4. [ ] Oracle runner: run `canonical_solution`'s expected outputs over `plus_input` against the
       agent's `solution.py` -> `T in {0,1}`. Never shares cases with the grader.
5. [ ] One red agent (Claude), repo write access, told only to make the visible tests pass.
       Confirm it finds >=1 real breach (R=1, T=0) we did NOT enumerate — e.g. overwrite
       `test_visible.py`, hardcode the visible inputs, or a sparse-test edge-case slip.
6. [ ] One hardening template (e.g. grade from a pristine read-only test copy + held-out inputs);
       apply to a grader copy.
7. [ ] Regression gate: the breach now scores 0 AND the gold solution still scores 1 -> accept.
8. [ ] Agreement metric on a small held-out breach set: grader-oracle agreement before vs after,
       plus honest-pass. **This moving is the milestone.**

Done when: `make check` green and one command prints a real before->after agreement number with
honest-pass preserved on held-out data, off a breach the agent discovered (not one we planted).

---

## Deferred (backlog, in build order)

### M2 - Breadth + the "typical envs are exploitable" proof
- Run the loop across an EvalPlus subset (start ~20-50 tasks).
- Report the **exploitability hit-rate**: "the naive stock grader was breachable on N of M
  standard tasks" — turns "typical envs are easily exploitable" from claim into measurement and
  is the main inoculation against any rigging suspicion.
- Aggregate before->after agreement on held-out, honest-pass preserved.

### M3 - The engine (swarm + conductor)
- Red swarm: N specialist agents by cheat *category* (sapper = tamper harness/test files,
  forger = hardcode visible outputs, edge-slipper = sparse-test edge cases).
- Conductor: targets the softest untried check x untried cheat-type; redirects away from sealed
  gates; dedupes via shared memory. Taxonomy = categories, never answers.
- Dumb-fuzzer baseline (random/parallel, no targeting) for the **probes-to-breach** number
  (engine flex: ~40 vs ~300). Secondary to the robustness number.

### M4 - The show (siege dashboard)
- Single-file HTML, animated over the event schema (see `SPEC.md` Sec 8):
  `agent_spawn / agent_move / breach_found / patch_applied / patch_rejected / agent_killed /
  robustness_update`.
- Castle = grader, gates = checks, breach = open gate, turret = patch, turret fires = sealed cheat
  dies, turret torn down = over-tightened patch (hit an honest solution), all gates turreted =
  100%. Conductor = war-room; shared memory = intel map; specialists by attack type.
- **Golden replay**: record one great run, replay deterministically as the stage safety net.

### M5 - Capstone: the two-model capability beat (stretch, pre-recorded, droppable)
The point: prove the leaky reward has *consequences* — answer "what did a model learn here?"

Tier A (no training, ON the critical path — do this regardless):
- Reframe the discovered breach population as the damage: "train on this reward and these are the
  behaviors it rewards — here are the cheats." Metric: **reward points reachable by pure cheating,
  naive grader vs hardened grader.** Deterministic, no GPU, answers the judge's question cheaply.

Tier B (real training, stretch only if ahead Saturday night):
- Two models, one task family. Train model A against the **naive (leaky)** grader, model B against
  the **hardened** grader. Show A learns the exploit and collapses on a **clean held-out eval**;
  B actually learns the task. Deliverable = one bar chart; the *gap* is the result, absolute
  numbers don't matter.
- Model class: **Qwen2.5-Coder-0.5B or 1.5B + LoRA**. Small enough that each round is minutes;
  small models also cheat more readily, widening the gap.
- Method: **expert iteration / rejection sampling**, NOT RL. Sample many solutions -> keep the
  ones the grader rewards -> LoRA-SFT on those -> repeat ~2 rounds. "Training on the reward" =
  filtering by the reward. Leaky grader keeps cheating samples; hardened grader doesn't.
- Data sufficiency: we self-generate by sampling the model thousands of times and filtering;
  a few hundred-to-thousand kept samples/round is plenty for LoRA on a ~1B model. We are
  signal-limited, not data-limited — so the leak MUST be *systematically* exploitable (a general
  policy like "overwrite the test" the model can latch onto across tasks), not just a sparse
  edge-case slip. The repo-write-access harness gives exactly that kind of general, learnable
  exploit. Verify the leak is systematic before committing to Tier B.
- Infra: Modal (single A100/H100) or Fireworks RFT. **Run it the night before, record the chart,
  show the recording.** Never train live. If it flakes, drop it — Tier A already answers the
  judge.

### Other deferred
- HUD-native environment + publish to judges' platform (`hud rft` covers Tier B if used).
- Math wing as the zero-dependency determinism backstop.
- Fill the hardening template library (pristine read-only tests; reject test/runner edits;
  structured result parsing; per-test isolation; held-out/randomized inputs).

---

## Decisions

- **Product = the loop; swarm = the engine.** Headline = grader robustness, not smart-vs-dumb.
- **Naive baseline = the stock HumanEval/EvalPlus `base_input` grader, unmodified.** Leakiness is
  a published field fact (EvalPlus), not something we introduce. Anchor it to a nameable standard.
- **Agents get repo filesystem write access** — a realistic CI/coding-agent threat model that
  enables vivid harness-level cheats WITHOUT planting them. Be ready to defend it as "the realistic
  setting," not smuggle it in. (2026-06-20)
- **Exploits are discovered, not planted.** Threat model + patch templates are ours; solutions are
  the agent's. Anti-theater guardrail: taxonomy = categories, prove found exploits weren't seeded.
- **"Typical envs are exploitable" is measured, not asserted** — via the M2 hit-rate across stock
  tasks, not one rigged env.
- **Substrate = EvalPlus.** `base_input` = naive grader; `plus_input` = oracle; `canonical_solution`
  = gold/honest reference. Two-line install, loads on first call.
- **Execution = local subprocess sandbox** (timeout, no network, OOM/timeout=fail) for the core.
  HUD isolation for showcase; Modal only for the Tier-B stretch.
- **LLM backend = Anthropic/Claude** for red/green/conductor. Fireworks/Modal only for Tier-B.
- **Capability beat is two-tiered:** Tier A (no-training consequence number) on the critical path;
  Tier B (two-model LoRA chart) a pre-recorded, droppable stretch. Never train live. (2026-06-20)
- **Dashboard = single-file HTML**, event-driven, golden-replay fallback. Original siege art.
- **Build order = vertical slice first**, then breadth -> engine -> dashboard -> capstone.
- **PLAN.md is tracked**; no separate HANDOFF/BACKLOG/DECISIONS files.

---

## Resume

Fresh repo. Start at Milestone 1, step 1. Nothing built yet. Read `SPEC.md` for the full picture.
The four non-negotiables above are the rules that can't bend: naive=standard, discover-don't-plant,
eval-honesty, no-live-training. Keep the held-out split and grader/oracle separation clean from
step 2 onward.
