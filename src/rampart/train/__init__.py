"""Target B (capstone) — the no-GPU data layer: expert-iteration arms from the rollout dataset.
Actual fine-tuning is gated on the abort line and runs on external infra (Modal/Fireworks/HUD RFT)."""

from .arms import Arm, SftExample, build_arms, write_sft

__all__ = ["Arm", "SftExample", "build_arms", "write_sft"]
