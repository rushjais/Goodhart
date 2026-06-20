"""Track C — the golden run is faithful to the script and replays in order onto the bus."""

import asyncio
import json
from pathlib import Path

from rampart.server import fakes
from rampart.server.bus import EventBus, to_wire
from rampart.server.replay import ReplayPublisher, load_golden

GOLDEN = Path(__file__).resolve().parents[1] / "golden_run.jsonl"


def test_golden_file_matches_the_siege_script():
    on_disk = [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]
    assert on_disk == [to_wire(e) for e in fakes.siege_script()]


def test_load_golden_validates_every_line_against_seam2():
    assert load_golden(GOLDEN) == fakes.siege_script()


def test_replay_emits_every_event_in_order():
    async def scenario():
        bus = EventBus()
        queue = bus.subscribe()
        await ReplayPublisher(GOLDEN, bus, delay=0.0).run()
        return [queue.get_nowait() for _ in range(queue.qsize())]

    assert asyncio.run(scenario()) == [to_wire(e) for e in fakes.siege_script()]
