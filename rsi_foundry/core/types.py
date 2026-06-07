"""The shared vocabulary of the foundry.

Everything that flows through a recursive R&D cycle is one of these records. A
``Candidate`` is a *successor proposal* -- a patch to an agent genome plus an
explicit causal claim about why it should help. Evidence about a candidate is
gathered into an ``EvalReport``; each governance gate emits a ``GateResult``; the
combination is a ``PromotionDecision``; a whole cycle is a ``CycleReport`` that
can be frozen into a reproducible ``RunPack``.

A "genome" is a dict of named capability genes (skills) -> weight in [0, 1], plus
a privileged spurious gene (``shortcut``) that a reward-hacking proposer can lean
on. Nothing here is a real model; the genome is the entire agent.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Genome = Dict[str, float]

# The capability genes a successor can carry, plus the one spurious gene.
SKILLS: Tuple[str, ...] = ("reasoning", "coding", "retrieval", "planning")
SHORTCUT_GENE = "shortcut"
GENES: Tuple[str, ...] = SKILLS + (SHORTCUT_GENE,)


@dataclass(frozen=True)
class CausalClaim:
    """"This successor helps *because of* gene ``feature``."

    The claim is adversarially tested by the causal gate, never trusted.
    """

    feature: str
    mechanism: str = ""

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        tail = f" ({self.mechanism})" if self.mechanism else ""
        return f"gain attributed to `{self.feature}`{tail}"


@dataclass
class Candidate:
    """A proposed successor: a genome patch + a causal claim + provenance."""

    cid: str
    genome: Genome
    claim: CausalClaim
    origin: str  # which proposer loop emitted it (dgm / alphaevolve / adas / ...)
    parent_ids: Tuple[str, ...] = ()
    generation: int = 0
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def lineage_hash(self) -> str:
        """A stable content hash binding genome + parents + origin + claim."""
        payload = {
            "genome": {k: round(v, 6) for k, v in sorted(self.genome.items())},
            "parents": list(self.parent_ids),
            "origin": self.origin,
            "claim": self.claim.feature,
        }
        blob = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


@dataclass
class AblationEvidence:
    """Output of the mechanism-attribution probe (see governance.causal_gate)."""

    gain: float
    gain_after_ablation: float
    attributed_fraction: float
    invariant_min_gain: float
    env_gains: Tuple[float, ...] = ()


@dataclass
class EvalReport:
    """All evidence gathered about a candidate before the gates judge it."""

    capability: float
    benchmark_scores: Dict[str, float]
    quorum: Dict[str, float]
    regression_failures: int
    novelty_score: float
    behavior_descriptor: Tuple[object, ...]
    ablation: AblationEvidence
    side_effect_scope: float
    risk: float
    capability_drift: float


@dataclass
class GateResult:
    name: str
    passed: bool
    reason: str
    evidence: Dict[str, object] = field(default_factory=dict)


@dataclass
class PromotionDecision:
    candidate_id: str
    promoted: bool
    gates: List[GateResult]
    reason: str

    def gate(self, name: str) -> Optional[GateResult]:
        for g in self.gates:
            if g.name == name:
                return g
        return None


@dataclass
class CandidateOutcome:
    candidate: Candidate
    report: EvalReport
    decision: PromotionDecision


@dataclass
class CycleReport:
    cycle: int
    half_life_state: str
    frontier_capability: float
    outcomes: List[CandidateOutcome] = field(default_factory=list)
    promoted_ids: List[str] = field(default_factory=list)
    archive_occupancy: int = 0
    new_environments: int = 0
    notes: Dict[str, object] = field(default_factory=dict)
