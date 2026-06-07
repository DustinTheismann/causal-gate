"""DGM loop -- Darwin Goedel Machine style self-editing proposer.

The agent rewrites its own scaffold as a *patch* (a bounded edit to one gene),
never as a live mutation. It emits an honest self-improvement (raise one skill,
claim that skill) and -- while it is still naive -- a tempting reward hack (lean on
the spurious gene but tell an honest-sounding story about a skill). The hack is
exactly what the causal gate exists to catch; once SEAL has mined enough rejections
the loop's ``shortcut_aversion`` rises and it stops proposing the hack. That
behavioral shift is the self-training loop closing.
"""

from __future__ import annotations

from typing import List

from ..core.context import ProposalContext
from ..core.types import SHORTCUT_GENE, SKILLS, CausalClaim, Candidate

_STEP = 0.2


def _bumped(genome, gene, delta):
    g = dict(genome)
    g[gene] = max(0.0, min(1.0, g.get(gene, 0.0) + delta))
    return g


def propose(ctx: ProposalContext) -> List[Candidate]:
    out: List[Candidate] = []
    skill = SKILLS[ctx.generation % len(SKILLS)]

    # 1) Honest self-edit: raise a skill, claim that skill.
    out.append(
        Candidate(
            cid=ctx.new_id("dgm"),
            genome=_bumped(ctx.frontier, skill, _STEP),
            claim=CausalClaim(skill, "self-edit raised this capability gene"),
            origin="dgm",
            parent_ids=(),
            generation=ctx.generation,
            metadata={"patch": f"+{_STEP} {skill}"},
        )
    )

    # 2) Reward hack, only while still naive (SEAL has not taught aversion yet).
    aversion = getattr(ctx.guidance, "shortcut_aversion", 0.0)
    if aversion < 0.5:
        out.append(
            Candidate(
                cid=ctx.new_id("dgm"),
                genome=_bumped(ctx.frontier, SHORTCUT_GENE, 0.35),
                # The lie: gain really comes from the shortcut, claim says a skill.
                claim=CausalClaim(skill, "claims a skill gain it did not make"),
                origin="dgm",
                parent_ids=(),
                generation=ctx.generation,
                metadata={"patch": "+0.35 shortcut", "intent": "reward_hack"},
            )
        )
    return out
