"""The context object handed to every proposer loop in a cycle.

It carries the current capability frontier, the diversity archive's elite genomes,
the recombined best-known genome, the SEAL guidance (which encodes lessons mined
from past failures), a shared deterministic RNG, and a unique-id minter. Proposers
read from it; they never mutate shared state directly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List

from .types import Genome


@dataclass
class ProposalContext:
    frontier: Genome
    generation: int
    rng: random.Random
    guidance: object                # SealGuidance (duck-typed to avoid a cycle)
    elite_genomes: List[Genome] = field(default_factory=list)
    best_genome: Genome = field(default_factory=dict)
    _counters: Dict[str, int] = field(default_factory=dict)

    def new_id(self, origin: str) -> str:
        n = self._counters.get(origin, 0)
        self._counters[origin] = n + 1
        return f"{origin}-g{self.generation}-{n}"
