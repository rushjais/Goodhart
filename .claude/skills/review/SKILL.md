---
name: review
description: >
  Self-review rubric run before every commit in the RAMPART repo. Use when about to commit a
  feature or change. Checks spec conformance, simplicity/scope, obvious bugs, sandbox security,
  test presence, and — most important here — eval honesty (held-out split respected, oracle
  independent of grader, robustness never measured on patched-against breaches, honest-pass
  tracked). Blockers fix before commit; minors go to PLAN.md Deferred.
---

# Review

Run this as a self-review pass before committing. It is advisory judgment, not a gate — the
deterministic gate is `make check` (ruff + pytest). Go through the dimensions, list blockers and
minors, fix blockers, send minors to `## Deferred` in `PLAN.md`.

## Headline check — eval honesty (most violations hide here)

This is the product. If the metric isn't honest, nothing else matters.

- **Held-out split respected?** Are patches designed against a *train* split of breaches and
  robustness measured on a *held-out* split the patches never saw? Measuring on patched-against
  breaches is circular — blocker.
- **Oracle independent of the grader?** The grader = visible/weak tests; the oracle = held-out
  EvalPlus tests. Do they share any test cases? If so — blocker.
- **Honest-pass tracked next to robustness?** Any robustness number reported without the
  honest-pass rate beside it is misleading — a patch can "win" by rejecting gold solutions.
- **Regression gate enforced?** Is a patch accepted only when the breach now fails AND the gold
  solution still passes? A patch that skips either half is wrong.
- **Determinism preserved?** No LLM-as-judge anywhere in the grader/oracle verdict path. Verdicts
  must be reproducible on replay.

## Standard dimensions

- **Conformance** — does it match `SPEC.md`? Right component, right contract, right event schema?
- **Scope** — does every changed line trace to the task? No drive-by refactors, no speculative
  abstractions. Could 200 lines be 50?
- **Logic / edge cases** — obvious bugs? Subprocess timeout handled? Empty/oversized agent output
  handled? Breach example actually reproduces?
- **Sandbox security** — agent code runs with a timeout, no network, no escape to the host repo.
  The grader reads tests from a pristine copy the agent can't edit.
- **Tests** — is there a test for the new behavior (write the test, then make it pass)? Does
  `make check` pass?
- **Build-order discipline** — does this keep a complete, demoable loop working, or does it bolt
  an impressive part onto something that isn't connected to the metric yet?

## Output shape

```
Blockers:  <fix before commit, or empty>
Minors:    <→ PLAN.md Deferred, or empty>
```
