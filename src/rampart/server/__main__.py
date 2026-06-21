"""`python -m rampart.server` — live engine; `--replay FILE` — golden replay safety net."""

import argparse
import asyncio
import socket

import uvicorn

from rampart.server.app import create_app
from rampart.server.bus import EventBus
from rampart.server.replay import ReplayPublisher

# The live run defaults to the HARDEST tasks (sparse tests vs tricky logic = where cheats
# actually surface), so the siege has real gates to breach. Override with --tasks.
N_DEMO_GATES = 4
_FALLBACK_TASKS = ["HumanEval/0", "HumanEval/2", "HumanEval/4", "HumanEval/8"]


def _default_task_ids(n: int = N_DEMO_GATES) -> list[str]:
    """The n hardest EvalPlus task ids; falls back to a fixed set if EvalPlus can't load."""
    try:
        from rampart.substrate import load_hardest

        return [t.task_id for t in load_hardest(n)]
    except Exception:
        return _FALLBACK_TASKS


def _ensure_port_free(host: str, port: int) -> None:
    """Fail loudly BEFORE uvicorn half-starts if the port is taken (stage safety)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError:
        raise SystemExit(
            f"error: {host}:{port} is already in use — a previous server is still bound.\n"
            f"  free it:  lsof -ti:{port} | xargs kill\n"
            f"  or run on another port:  python -m rampart.server --port <N> [--replay FILE]"
        ) from None
    finally:
        probe.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="rampart.server")
    parser.add_argument("--replay", metavar="FILE", help="stream a recorded golden run")
    parser.add_argument("--speed", type=float, default=1.0, help="replay speed multiplier")
    parser.add_argument("--tasks", help="comma-separated EvalPlus task ids for the live run")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    bus = EventBus()
    if args.replay:
        publisher = ReplayPublisher(args.replay, bus, speed=args.speed)

        async def startup():
            await bus.connected.wait()  # hold until the dashboard connects
            await publisher.run()
    else:
        # Live: the conductor already emits the 7 locked Seam 2 dataclasses through `emit`,
        # so emit=bus.emit is a drop-in — identical wire format, no dashboard change.
        try:
            from rampart.breadth.loop import maybe_client
            from rampart.conductor.live import run_live
        except ModuleNotFoundError as exc:
            raise SystemExit(
                f"error: live engine not importable ({exc.name}). This branch needs the engine "
                f"(merge main → track-c), or run the golden replay safety net instead:\n"
                f"  make demo"
            ) from None

        task_ids = args.tasks.split(",") if args.tasks else _default_task_ids()
        client = maybe_client()

        async def startup():
            loop = asyncio.get_running_loop()

            # The bus uses asyncio.Queue (not thread-safe); run_live is sync and runs in a
            # worker thread, so marshal each emit back onto the loop. No connected.wait here:
            # the live engine runs on its own; late browsers catch up via the bus backlog.
            def emit(event):
                loop.call_soon_threadsafe(bus.emit, event)

            await asyncio.to_thread(run_live, task_ids, client=client, emit=emit)

    _ensure_port_free(args.host, args.port)
    print(f"siege dashboard → http://{args.host}:{args.port}")
    uvicorn.run(create_app(bus, startup=startup), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
