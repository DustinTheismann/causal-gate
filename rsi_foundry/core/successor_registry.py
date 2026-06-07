"""Registry of promoted successors and the lineage graph.

Holds the live capability frontier (the genome every proposer builds on) and an
append-only record of promotions, each bound to its content ``lineage_hash``. The
lineage edges make the recursive ancestry of any successor reconstructable -- the
audit substrate for "where did this capability come from".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .types import Candidate, EvalReport, Genome


@dataclass
class Promotion:
    cid: str
    lineage_hash: str
    origin: str
    capability: float
    parent_ids: Tuple[str, ...]
    claim: str


@dataclass
class SuccessorRegistry:
    frontier_genome: Genome
    frontier_capability: float
    promotions: List[Promotion] = field(default_factory=list)
    lineage: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    def promote(self, candidate: Candidate, report: EvalReport) -> Promotion:
        promo = Promotion(
            cid=candidate.cid,
            lineage_hash=candidate.lineage_hash,
            origin=candidate.origin,
            capability=report.capability,
            parent_ids=candidate.parent_ids,
            claim=candidate.claim.feature,
        )
        self.promotions.append(promo)
        self.lineage[candidate.cid] = candidate.parent_ids
        # The promoted successor becomes the new frontier all proposers extend.
        self.frontier_genome = dict(candidate.genome)
        self.frontier_capability = report.capability
        return promo

    def lineage_edges(self) -> List[Tuple[str, str]]:
        return [(parent, child) for child, parents in self.lineage.items() for parent in parents]

    def latest(self) -> List[str]:
        return [p.cid for p in self.promotions]
