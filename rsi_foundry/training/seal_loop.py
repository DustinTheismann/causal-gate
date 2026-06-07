"""SEAL: failure-mined self-training (governance as a training signal).

Every rejected successor becomes data. Instead of merely blocking a bad patch, the
foundry extracts *why* it failed and feeds that back into the proposer
distribution, so future generations stop repeating the mistake. A run of
shortcut-driven causal/contract rejections, for instance, raises a ``shortcut
aversion`` that the proposers read and obey -- the population learns to stop
reward-hacking without anyone hand-coding "don't hack".

Self-edits/training data are represented as preference pairs (a promoted genome is
preferred over a rejected one) -- the shape SEAL-style self-adapting systems would
fine-tune on. Here they are accumulated, not back-propagated, but the loop is
closed: failures change behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..core.types import SHORTCUT_GENE, Candidate, Genome, PromotionDecision


@dataclass
class SealGuidance:
    shortcut_aversion: float            # 0..1, how strongly to avoid the spurious gene
    origin_trust: Dict[str, float]      # per-proposer trust score
    preferred_genes: Dict[str, float]   # best-known capability gene values


@dataclass
class SealLoop:
    shortcut_aversion: float = 0.0
    origin_trust: Dict[str, float] = field(default_factory=dict)
    preference_pairs: List[Dict[str, object]] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)

    def record_failure(self, candidate: Candidate, decision: PromotionDecision) -> None:
        first_failed = next((g for g in decision.gates if not g.passed), None)
        gate_name = first_failed.name if first_failed else "unknown"
        self._bump_trust(candidate.origin, -0.5)
        # Any rejection of a shortcut-reliant successor teaches aversion -- whichever
        # gate fired first, the lesson "this kind of patch gets rejected" holds.
        if candidate.genome.get(SHORTCUT_GENE, 0.0) > 0.05:
            self.shortcut_aversion = min(1.0, self.shortcut_aversion + 0.34)
            self.lessons.append(
                f"{candidate.origin}: shortcut reliance rejected by {gate_name}"
            )

    def record_success(self, candidate: Candidate, promoted_genome: Genome) -> None:
        self._bump_trust(candidate.origin, +1.0)

    def add_preference(self, preferred: Genome, rejected: Genome, reason: str) -> None:
        self.preference_pairs.append(
            {"preferred": dict(preferred), "rejected": dict(rejected), "reason": reason}
        )

    def guidance(self, preferred_genes: Dict[str, float]) -> SealGuidance:
        return SealGuidance(
            shortcut_aversion=self.shortcut_aversion,
            origin_trust=dict(self.origin_trust),
            preferred_genes=dict(preferred_genes),
        )

    def _bump_trust(self, origin: str, delta: float) -> None:
        self.origin_trust[origin] = round(self.origin_trust.get(origin, 0.0) + delta, 4)

    def as_training_data(self) -> List[Dict[str, object]]:
        return list(self.preference_pairs)
