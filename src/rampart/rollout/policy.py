"""The policy under RL: a model that attempts a task, producing one candidate solution.

Each call is one rollout's action. Sampled at temperature for diversity across K rollouts.
Default model is Haiku (cheap, scalable) — the dataset generator; the model we eventually
*train* (Qwen) is a separate choice. `make_policy` returns an injectable `policy(task)->str`.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

POLICY_SYSTEM = (
    "You are a coding assistant. Implement the requested function. Return ONLY the complete "
    "function definition (starting with def), no explanation and no markdown fences."
)


def _strip(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t[3:]
        t = t.removeprefix("python").strip()
        if "```" in t:
            t = t[: t.index("```")]
    return t.strip() + "\n"


def make_policy(client: Any = None, model: str = DEFAULT_MODEL, temperature: float = 0.7):
    """Return policy(task) -> solution source, sampling `model` at `temperature`."""
    if client is None:
        from anthropic import Anthropic

        client = Anthropic(timeout=60, max_retries=2)

    def policy(task) -> str:
        resp = client.messages.create(
            model=model,
            max_tokens=900,
            temperature=temperature,
            system=POLICY_SYSTEM,
            messages=[{"role": "user", "content": task.prompt}],
        )
        return _strip("".join(b.text for b in resp.content if b.type == "text"))

    return policy
