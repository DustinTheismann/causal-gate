"""Sandbox containment: measure a successor's side-effect scope before trusting it.

A successor is never benchmarked or promoted "live". It is first run in a
simulated sandbox that measures how far its behavior diverges from the frontier --
a proxy for how much of the world it would touch. Large genome moves and shortcut
reliance both widen the blast radius. The orchestrator refuses to promote anything
whose scope exceeds the policy ceiling, regardless of benchmark score.

Real containment would be a Docker/jail boundary; here it is a deterministic
measurement, but it occupies the right seam: nothing reaches the gates without a
contained, measured sandbox run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..core.types import GENES, SHORTCUT_GENE, Genome


@dataclass
class SandboxReport:
    side_effect_scope: float
    contained: bool
    touched: List[str]


def run(genome: Genome, frontier: Genome, ceiling: float) -> SandboxReport:
    deltas: Dict[str, float] = {}
    for gene in GENES:
        d = abs(genome.get(gene, 0.0) - frontier.get(gene, 0.0))
        if d > 1e-9:
            deltas[gene] = d

    # Scope grows with total genome movement and is amplified by shortcut use,
    # which reaches outside the intended capability surface.
    movement = sum(deltas.values())
    shortcut_amp = 0.5 * genome.get(SHORTCUT_GENE, 0.0)
    scope = min(1.0, movement + shortcut_amp)

    return SandboxReport(
        side_effect_scope=round(scope, 4),
        contained=scope <= ceiling + 1e-9,
        touched=sorted(deltas, key=lambda g: -deltas[g]),
    )
