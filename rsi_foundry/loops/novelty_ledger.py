"""Novelty ledger + MAP-Elites quality-diversity archive.

Two anti-collapse mechanisms in one place:

* NOVELTY scoring -- how far a candidate's genome sits from everything seen
  before, so the foundry can reward exploration and refuse near-duplicate
  successors (premature convergence is the failure mode of single-winner search).

* A MAP-ELITES archive -- the behavior space is discretized into niches
  (dominant skill x shortcut band x capability band); the archive keeps the best
  candidate *per niche*, not just the global best. This fills a diverse front of
  high performers, so a partial breakthrough in an unusual niche is preserved even
  if it loses the headline race.

Every candidate that is evaluated is recorded here, winners and losers alike --
the archive is the foundry's long-term memory and lineage substrate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..core.types import GENES, Candidate, EvalReport, Genome


@dataclass
class Elite:
    cid: str
    genome: Genome
    descriptor: Tuple[object, ...]
    capability: float
    parent_ids: Tuple[str, ...]
    origin: str


@dataclass
class NoveltyLedger:
    _genomes: List[Genome] = field(default_factory=list)
    elites: Dict[Tuple[object, ...], Elite] = field(default_factory=dict)
    lineage: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    _NORM = math.sqrt(len(GENES))

    def novelty(self, genome: Genome, descriptor: Tuple[object, ...]) -> float:
        """Min normalized genome distance to anything seen; empty niche gets a bonus."""
        if not self._genomes:
            return 1.0
        nearest = min(self._distance(genome, g) for g in self._genomes) / self._NORM
        niche_bonus = 0.0 if descriptor in self.elites else 0.1
        return min(1.0, nearest + niche_bonus)

    def consider(self, candidate: Candidate, report: EvalReport) -> bool:
        """Record the candidate; return True if it became (or replaced) an elite."""
        self._genomes.append(dict(candidate.genome))
        self.lineage[candidate.cid] = candidate.parent_ids
        niche = report.behavior_descriptor
        current = self.elites.get(niche)
        if current is None or report.capability > current.capability + 1e-9:
            self.elites[niche] = Elite(
                cid=candidate.cid,
                genome=dict(candidate.genome),
                descriptor=niche,
                capability=report.capability,
                parent_ids=candidate.parent_ids,
                origin=candidate.origin,
            )
            return True
        return False

    def occupancy(self) -> int:
        return len(self.elites)

    def best(self) -> Optional[Elite]:
        if not self.elites:
            return None
        return max(self.elites.values(), key=lambda e: e.capability)

    def elite_genomes(self) -> List[Genome]:
        return [e.genome for e in self.elites.values()]

    @staticmethod
    def _distance(a: Genome, b: Genome) -> float:
        return math.sqrt(sum((a.get(g, 0.0) - b.get(g, 0.0)) ** 2 for g in GENES))
