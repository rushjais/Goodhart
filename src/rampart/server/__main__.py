"""`python -m rampart.server [--replay FILE]` — golden replay now, live engine wired in last."""

import argparse

import uvicorn

from rampart.server.app import create_app
from rampart.server.bus import EventBus
from rampart.server.replay import ReplayPublisher


def main() -> None:
    parser = argparse.ArgumentParser(prog="rampart.server")
    parser.add_argument("--replay", metavar="FILE", help="stream a recorded golden run")
    parser.add_argument("--speed", type=float, default=1.0, help="replay speed multiplier")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    bus = EventBus()
    startup = None
    if args.replay:
        publisher = ReplayPublisher(args.replay, bus, speed=args.speed)

        async def startup():
            await bus.connected.wait()  # hold until the dashboard connects
            await publisher.run()
    # else: the live engine (Track A/B) calls bus.emit — wired in last.

    print(f"siege dashboard → http://{args.host}:{args.port}")
    uvicorn.run(create_app(bus, startup=startup), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
