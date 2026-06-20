.PHONY: check fmt lint test install dev demo

# Deterministic gate — the same thing the Stop hook and pre-commit run.
check: lint test

lint:
	ruff format --check .
	ruff check .

test:
	pytest -q

fmt:
	ruff format .
	ruff check --fix .

install:
	uv sync

# Run the loop with the event backend + serve the dashboard (filled in at Milestone 4).
dev:
	uv run python -m rampart.server

# Replay the recorded golden run — the stage safety net.
demo:
	uv run python -m rampart.server --replay golden_run.jsonl
