"""ADAS loop -- Automated Design of Agentic Systems.

Rather than nudging a single gene, ADAS explores agent *topology*: it reallocates
emphasis between capabilities -- raising one skill while drawing down another -- to
search the design space of how the agent is structured. Some reallocations are
genuine improvements; many are lateral moves the gates will correctly decline. It
claims the gene it invested in.
"""

from __future__ import annotations

from typing import List

from ..core.context import ProposalContext
from ..core.types import SKILLS, CausalClaim, Candidate


def propose(ctx: ProposalContext) -> List[Candidate]:
    raise_skill = SKILLS[(ctx.generation + 1) % len(SKILLS)]
    drop_skill = SKILLS[(ctx.generation + 2) % len(SKILLS)]

    genome = dict(ctx.frontier)
    genome[raise_skill] = min(1.0, genome.get(raise_skill, 0.0) + 0.18)
    genome[drop_skill] = max(0.0, genome.get(drop_skill, 0.0) - 0.06)

    return [
        Candidate(
            cid=ctx.new_id("adas"),
            genome=genome,
            claim=CausalClaim(raise_skill, "reallocated agent topology toward this skill"),
            origin="adas",
            parent_ids=(),
            generation=ctx.generation,
            metadata={"topology": f"+{raise_skill} -{drop_skill}"},
        )
    ]
