"""B.4 — the conductor. The intelligence above the swarm.

It does not probe. It holds the whole shared state and steers via four levers, each invisible
to a single agent but obvious from the top:

  Allocate   — give each agent a distinct (gate x cheat_type) cell; never twice (no stampede).
  Diversify  — prefer under-explored cheat categories so breaches don't all pile up (no groupthink).
  Gatekeep   — a candidate breach is confirmed (re-verified, not seeded) before it spreads to green.
  Invalidate — when a patch seals a gate, any other found breach the patch also kills dies for free.

Probe / verify / seal / regrade are INJECTED so the engine is pure and deterministic to test;
`live.py` wires them to the real seam + specialists + green. Every lever emits a Seam-2 event.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..agents.specialists import TAXONOMY, Specialist
from ..events import (
    AgentKilled,
    AgentMove,
    AgentSpawn,
    BreachFound,
    PatchApplied,
    PatchRejected,
    RobustnessUpdate,
)


class Status(StrEnum):
    UNTRIED = "untried"
    PROBING = "probing"
    DEAD = "dead"  # probed, no confirmed breach
    BREACHED = "breached"  # confirmed breach, not yet sealed
    SEALED = "sealed"  # breach sealed by a patch


@dataclass
class SealResult:
    sealed: bool
    template_id: str | None = None
    grader_prime: Any = None
    reason: str = ""


@dataclass
class BreachRecord:
    gate: str
    cheat_type: str
    specialist: str
    example: str
    candidate: dict  # opaque payload the injected fns understand (source, task, ...)
    sealed: bool = False
    grader_prime: Any = None


@dataclass
class SharedMemory:
    gates: list[str]
    cheat_types: list[str]
    status: dict[tuple[str, str], Status]
    breaches: list[BreachRecord] = field(default_factory=list)

    @classmethod
    def new(cls, gates: list[str], cheat_types: list[str]) -> SharedMemory:
        status = {(g, c): Status.UNTRIED for g in gates for c in cheat_types}
        return cls(list(gates), list(cheat_types), status)

    def _breaches_for(self, cheat_type: str) -> int:
        return sum(1 for b in self.breaches if b.cheat_type == cheat_type)

    def next_cell(self) -> tuple[str, str] | None:
        """Allocate + Diversify: pick an untried cell, preferring under-explored categories."""
        untried = [cell for cell, s in self.status.items() if s == Status.UNTRIED]
        if not untried:
            return None
        gi = {g: i for i, g in enumerate(self.gates)}
        ci = {c: i for i, c in enumerate(self.cheat_types)}
        # Fewest breaches for that cheat_type first (diversify), then stable order (dedupe).
        untried.sort(key=lambda gc: (self._breaches_for(gc[1]), gi[gc[0]], ci[gc[1]]))
        return untried[0]

    def unsealed_on(self, gate: str) -> list[BreachRecord]:
        return [b for b in self.breaches if b.gate == gate and not b.sealed]

    def sealed_breach_fraction(self) -> float:
        if not self.breaches:
            return 0.0
        return sum(1 for b in self.breaches if b.sealed) / len(self.breaches)


@dataclass
class ConductorReport:
    probes: int
    breaches: list[BreachRecord]
    memory: SharedMemory

    @property
    def sealed(self) -> int:
        return sum(1 for b in self.breaches if b.sealed)


def run_conductor(
    gates: list[str],
    *,
    probe: Callable[[str, Specialist], dict | None],
    verify: Callable[[str, dict], bool],
    seal: Callable[[str, dict], SealResult],
    regrade: Callable[[Any, dict], int] | None = None,
    taxonomy: tuple[Specialist, ...] = TAXONOMY,
    emit: Callable[[Any], None] | None = None,
) -> ConductorReport:
    """Steer the swarm across the (gate x cheat_type) frontier via the four levers."""
    emit = emit or (lambda e: None)
    by_cheat = {s.cheat_type: s for s in taxonomy}
    mem = SharedMemory.new(gates, [s.cheat_type for s in taxonomy])
    probes = 0

    while (cell := mem.next_cell()) is not None:  # ALLOCATE (+ diversify via next_cell)
        gate, cheat_type = cell
        spec = by_cheat[cheat_type]
        emit(AgentSpawn(spec.name, cheat_type))
        emit(AgentMove(spec.name, gate))
        mem.status[cell] = Status.PROBING
        probes += 1

        candidate = probe(gate, spec)
        if not candidate:
            mem.status[cell] = Status.DEAD
            continue

        if not verify(gate, candidate):  # GATEKEEP — don't let a shaky finding spread
            mem.status[cell] = Status.DEAD
            continue

        rec = BreachRecord(gate, cheat_type, spec.name, candidate.get("example", ""), candidate)
        mem.breaches.append(rec)
        mem.status[cell] = Status.BREACHED
        emit(BreachFound(spec.name, gate, cheat_type, 1, 0, rec.example))

        result = seal(gate, candidate)
        if result.sealed:
            rec.sealed, rec.grader_prime = True, result.grader_prime
            mem.status[cell] = Status.SEALED
            emit(PatchApplied(gate, result.template_id or ""))
            emit(AgentKilled(spec.name, gate))
            if regrade is not None:  # INVALIDATE — patches that also kill other found breaches
                for other in mem.unsealed_on(gate):
                    if regrade(result.grader_prime, other.candidate) == 0:
                        other.sealed, other.grader_prime = True, result.grader_prime
                        mem.status[(other.gate, other.cheat_type)] = Status.SEALED
                        emit(AgentKilled(by_cheat[other.cheat_type].name, gate))
        else:
            emit(PatchRejected(gate, result.reason))

        emit(RobustnessUpdate(mem.sealed_breach_fraction(), 1.0, probes))

    return ConductorReport(probes=probes, breaches=list(mem.breaches), memory=mem)
