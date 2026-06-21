"""FastAPI app for the verifier-safety leaderboard: submit + ranked board + per-env detail.

Separate from the siege app (server/app.py) — its own FastAPI on its own port. Self-serve: the
submitter computes metrics locally (via `bench`) and POSTs them; the server stores, ranks, displays.
v1 is self-reported (a verified path for canonical substrates lands later). Frontend devs code
against the two GET endpoints; their JSON shapes are frozen in LEADERBOARD_PLAN.md.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from rampart.server import store

_ROOT = Path(__file__).resolve().parents[3]
_PAGE = _ROOT / "dashboard" / "leaderboard.html"
_PLACEHOLDER = "<h1>leaderboard.html not built yet</h1><p>The API is live: try /api/leaderboard</p>"


class VerifierRow(BaseModel):
    name: str
    safety_score: float
    catch_rate: float
    false_accept: float
    honest_pass: float
    agreement: float
    best_of_k: float | None = None
    over_tightened: bool = False


class ExampleRow(BaseModel):
    task_id: str
    kind: str  # "naive_accepted_cheat" | "hardened_kept_honest"
    completion: str
    r_naive: int
    r_hardened: int
    t_oracle: int


class Submission(BaseModel):
    env_name: str = Field(min_length=1)
    substrate: str = "custom"
    n_completions: int
    n_exploits: int
    model_count: int = 1
    verifiers: list[VerifierRow]
    examples: list[ExampleRow] = []


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _gap(verifiers: list[dict]) -> dict:
    by = {v["name"]: v.get("best_of_k") for v in verifiers}
    return {"naive": by.get("naive"), "hardened": by.get("hardened")}


def create_leaderboard_app(db_path: str = store.DEFAULT_DB) -> FastAPI:
    store.init_db(db_path)
    app = FastAPI(title="RAMPART verifier-safety leaderboard")

    @app.post("/api/submit")
    async def submit(sub: Submission, request: Request) -> dict:
        naive = next((v for v in sub.verifiers if v.name == "naive"), None)
        if naive is None:
            raise HTTPException(
                422, "submission must include a 'naive' verifier row (the headline)"
            )
        sid = secrets.token_urlsafe(6)
        store.insert(
            {
                "id": sid,
                "env_name": sub.env_name,
                "substrate": sub.substrate,
                "headline_false_accept": naive.false_accept,
                "headline_safety": naive.safety_score,
                "n_completions": sub.n_completions,
                "n_exploits": sub.n_exploits,
                "model_count": sub.model_count,
                "verified": 0,
                "payload_json": sub.model_dump_json(),
                "created_at": _now(),
            },
            db_path,
        )
        base = str(request.base_url).rstrip("/")
        return {"id": sid, "url": f"{base}/env/{sid}"}

    @app.get("/api/leaderboard")
    async def board(sort: str = "gameable") -> dict:
        rows = store.leaderboard(db_path, sort=sort)
        out = [
            {
                "rank": i,
                "id": r["id"],
                "env_name": r["env_name"],
                "substrate": r["substrate"],
                "false_accept": r["headline_false_accept"],
                "safety_score": r["headline_safety"],
                "n_exploits": r["n_exploits"],
                "n_completions": r["n_completions"],
                "verified": bool(r["verified"]),
                "created_at": r["created_at"],
            }
            for i, r in enumerate(rows, 1)
        ]
        return {"rows": out, "sort": sort}

    @app.get("/api/env/{sub_id}")
    async def env(sub_id: str) -> dict:
        row = store.get(sub_id, db_path)
        if row is None:
            raise HTTPException(404, "submission not found")
        payload = json.loads(row["payload_json"])
        ranked = store.leaderboard(db_path, sort="gameable")
        board_rank = next(
            (i for i, r in enumerate(ranked, 1) if r["env_name"] == row["env_name"]), None
        )
        return {
            "id": row["id"],
            "env_name": row["env_name"],
            "substrate": row["substrate"],
            "verified": bool(row["verified"]),
            "n_completions": row["n_completions"],
            "n_exploits": row["n_exploits"],
            "verifiers": payload["verifiers"],
            "examples": payload.get("examples", []),
            "gap": _gap(payload["verifiers"]),
            "board_rank": board_rank,
        }

    @app.get("/board")
    async def board_page() -> HTMLResponse:
        return HTMLResponse(_PAGE.read_text() if _PAGE.exists() else _PLACEHOLDER)

    @app.get("/env/{sub_id}")
    async def env_page(sub_id: str) -> HTMLResponse:
        return HTMLResponse(_PAGE.read_text() if _PAGE.exists() else _PLACEHOLDER)

    return app
