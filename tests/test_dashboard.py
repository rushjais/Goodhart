"""Track C — the dashboard is served and has a render path for every locked event type."""

from pathlib import Path

from starlette.testclient import TestClient

from rampart.server.app import create_app
from rampart.server.bus import EventBus

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard" / "index.html"
SEAM2_TAGS = {
    "agent_spawn",
    "agent_move",
    "breach_found",
    "patch_applied",
    "patch_rejected",
    "agent_killed",
    "robustness_update",
}


def test_dashboard_is_served_at_root():
    with TestClient(create_app(EventBus())) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "GOODHART" in resp.text


def test_dashboard_handles_every_seam2_event_type():
    html = DASHBOARD.read_text()
    for tag in SEAM2_TAGS:
        assert f"{tag}(e)" in html or f"{tag}(" in html, f"no render path for {tag}"
