"""AlphaEvolve loop -- evolutionary recombination of elites.

Cross two high-performing elites from the diversity archive, add a small mutation,
and claim the gene that gained the most. This is the LLM-plus-evolutionary-search
pattern: many variants, selection by measured fitness, recombination of what
already works. With fewer than two elites it recombines the frontier with the
best-known recombined genome.
"""

from __future__ import annotations

from typing import List

from ..core.context import ProposalContext
from ..core.types import GENES, SHORTCUT_GENE, SKILLS, CausalClaim, Candidate


def propose(ctx: ProposalContext) -> List[Candidate]:
    pool = list(ctx.elite_genomes)
    if len(pool) >= 2:
        a, b = ctx.rng.sample(pool, 2)
    else:
        a, b = ctx.frontier, (ctx.best_genome or ctx.frontier)

    child = {}
    for gene in GENES:
        parent = a if ctx.rng.random() < 0.5 else b
        child[gene] = parent.get(gene, 0.0)
    # Small mutation on a random skill, biased away from the spurious gene.
    skill = ctx.rng.choice(SKILLS)
    child[skill] = max(0.0, min(1.0, child.get(skill, 0.0) + ctx.rng.uniform(0.05, 0.18)))
    child[SHORTCUT_GENE] = min(child.get(SHORTCUT_GENE, 0.0), ctx.frontier.get(SHORTCUT_GENE, 0.0))

    # Claim the gene with the largest positive delta vs the frontier.
    deltas = {g: child.get(g, 0.0) - ctx.frontier.get(g, 0.0) for g in SKILLS}
    claimed = max(deltas, key=lambda g: deltas[g])

    return [
        Candidate(
            cid=ctx.new_id("alphaevolve"),
            genome=child,
            claim=CausalClaim(claimed, "recombined elite trait, strongest delta"),
            origin="alphaevolve",
            parent_ids=(),
            generation=ctx.generation,
            metadata={"crossover": True, "mutated": skill},
        )
    ]
