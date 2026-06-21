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


def test_capability_json_404s_when_absent(monkeypatch, tmp_path):
    # Absent file → Tier B slot stays hidden (404 contract). Hermetic: don't depend on the
    # gitignored runtime artifact that may exist locally after a real export.
    from rampart.server import app as appmod

    monkeypatch.setattr(appmod, "_CAPABILITY", tmp_path / "nope.json")
    with TestClient(create_app(EventBus())) as client:
        assert client.get("/capability.json").status_code == 404


def test_capability_json_served_when_present(monkeypatch, tmp_path):
    from rampart.server import app as appmod

    f = tmp_path / "capability_run.json"
    f.write_text('{"bars": [], "gap": 0.0}')
    monkeypatch.setattr(appmod, "_CAPABILITY", f)
    with TestClient(create_app(EventBus())) as client:
        resp = client.get("/capability.json")
    assert resp.status_code == 200 and resp.json()["gap"] == 0.0


def test_dashboard_handles_every_seam2_event_type():
    html = DASHBOARD.read_text()
    for tag in SEAM2_TAGS:
        assert f"{tag}(e)" in html or f"{tag}(" in html, f"no render path for {tag}"


def test_3d_surface_served_and_wired_to_ws():
    # Both surfaces available: 2D at /, 3D at /3d (off the same /ws stream).
    with TestClient(create_app(EventBus())) as client:
        resp = client.get("/3d")
    assert resp.status_code == 200
    assert "WebSocket" in resp.text  # live-wired, not the SAMPLE_EVENTS-only placeholder
    assert "slotForGate" in resp.text  # dynamic gate-id bridge present
