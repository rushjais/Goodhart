"""HUD trace-logging for the verifier leaderboard — make a RAMPART eval observable on hud.ai.

Wraps a leaderboard run as a HUD trace: each verifier scored is a span, and the final best-of-K
gap is reported as the trace's reward. Degrades gracefully — no hud-python, no HUD_API_KEY, or any
HUD error → falls back to the plain (untraced) leaderboard. It never crashes the pipeline.

Mechanism (hud-python 0.6.6, validated): @hud.instrument records spans; trace_enter registers the
trace BEFORE spans (the upload endpoint 404s on an unknown id); flush uploads + writes <id>.jsonl
locally (HUD_TELEMETRY_LOCAL_DIR, works with no key); _report finalizes with a reward.
"""

from __future__ import annotations

import os
import uuid

from ..rollout.dataset import Rollout
from .core import Verdict, VerifierScore, column, leaderboard, score_verifier
from .gap import bestofk_gap


def hud_available() -> bool:
    try:
        import hud  # noqa: F401

        return True
    except Exception:
        return False


def _default_verifiers() -> list[tuple[str, Verdict]]:
    return [("naive", column("r_naive")), ("hardened", column("r_hardened"))]


def trace_leaderboard(
    rollouts: list[Rollout],
    verifiers: list[tuple[str, Verdict]] | None = None,
    *,
    model: str = "rampart-bench",
    local_dir: str | None = "runs/_hud_traces",
) -> list[VerifierScore]:
    """Score the leaderboard inside a HUD trace; return the rows. Safe with no key / no hud."""
    verifiers = verifiers or _default_verifiers()
    if not hud_available():
        return leaderboard(rollouts, verifiers)
    try:
        import asyncio

        return asyncio.run(_traced(rollouts, verifiers, model=model, local_dir=local_dir))
    except Exception as e:  # any HUD/version issue → never break the pipeline
        print(f"[hud] tracing unavailable ({e}); returning untraced leaderboard")
        return leaderboard(rollouts, verifiers)


async def _traced(rollouts, verifiers, *, model, local_dir):
    import hud
    from hud.eval.job import _report, trace_enter
    from hud.settings import settings
    from hud.telemetry import flush
    from hud.telemetry.context import set_trace_context

    if local_dir:
        os.environ.setdefault("HUD_TELEMETRY_LOCAL_DIR", local_dir)
        settings.telemetry_local_dir = local_dir

    trace_id = uuid.uuid4().hex
    await trace_enter(
        trace_id, job_id=None, group_id=None, model=model
    )  # before any spans (404 guard)
    rows: list[VerifierScore] = []
    with set_trace_context(trace_id):
        for name, verdict in verifiers:

            @hud.instrument(name=f"rampart.verifier.{name}")
            def _run(v=verdict, n=name):
                return score_verifier(rollouts, v, name=n)

            rows.append(_run())
        gap = bestofk_gap(rollouts)

    flush(timeout=10.0)
    await _report(f"/trace/{trace_id}/exit", {"status": "completed", "reward": float(gap.gap)})
    if settings.api_key:
        print(f"[hud] view: {settings.hud_web_url}/traces/{trace_id}")
    else:
        print(f"[hud] no key — spans dumped locally to {local_dir}/{trace_id}.jsonl")
    return rows
