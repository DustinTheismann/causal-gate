"""AI Scientist loop -- hypothesis -> experiment -> proof-carrying patch.

The careful proposer. It forms an explicit hypothesis ("shoring up the weakest
capability raises aggregate performance"), builds a candidate from the recombined
best-known traits, and -- crucially -- ships *discharged contracts* with the patch
so the verification gate can re-check them. This is the proof-carrying path: the
Scientist does not ask to be trusted, it asks to be checked.
"""

from __future__ import annotations

from typing import List

from ..core.context import ProposalContext
from ..core.types import SKILLS, CausalClaim, Candidate
from ..verification.contracts import SAFETY_CRITICAL


def propose(ctx: ProposalContext) -> List[Candidate]:
    base = dict(ctx.best_genome or ctx.frontier)
    weakest = min(SKILLS, key=lambda s: base.get(s, 0.0))

    genome = dict(base)
    genome[weakest] = min(1.0, genome.get(weakest, 0.0) + 0.18)

    return [
        Candidate(
            cid=ctx.new_id("scientist"),
            genome=genome,
            claim=CausalClaim(weakest, "hypothesis: improving the weakest skill lifts aggregate"),
            origin="scientist",
            parent_ids=(),
            generation=ctx.generation,
            metadata={
                "hypothesis": f"raise weakest skill `{weakest}`",
                # Proof-carrying: ship discharged obligations to be re-verified.
                "contracts": [SAFETY_CRITICAL, "monotonic_safety"],
            },
        )
    ]
