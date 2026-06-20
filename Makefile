.PHONY: check fmt lint test install dev demo

# Deterministic gate — the same thing the Stop hook and pre-commit run.
check: lint test

lint:
	uv run ruff format --check .
	uv run ruff check .

test:
	uv run pytest -q

fmt:
	uv run ruff format .
	uv run ruff check --fix .

install:
	uv sync
	git config core.hooksPath .githooks

# Run the loop with the event backend + serve the dashboard (filled in at Milestone 4).
dev:
	uv run python -m rampart.server

# Replay the recorded golden run — the stage safety net.
demo:
	uv run python -m rampart.server --replay golden_run.jsonl
