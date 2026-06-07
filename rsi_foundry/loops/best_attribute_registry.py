"""Best Attribute Registry: harvest useful traits from every candidate.

Single-winner search throws away losers wholesale. But a rejected successor often
contains a *partial* breakthrough -- the best retrieval gene seen so far, a safer
shortcut profile, a stronger planning value -- even though its overall package
failed the gates. This registry tracks the best observed value of each gene
(scoped to candidates that did no harm on protected tasks), together with the
lineage it came from, so a future proposer can recombine the best parts of many
losers into a candidate that wins.

This is the "recursive improvement without single-winner fixation" move: the
generator gets better because the archive remembers what worked, not just who won.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from ..core.types import GENES, SHORTCUT_GENE, Candidate, EvalReport, Genome


@dataclass
class TraitRecord:
    gene: str
    value: float
    source_cid: str
    source_origin: str


@dataclass
class BestAttributeRegistry:
    records: Dict[str, TraitRecord] = field(default_factory=dict)

    def update(self, candidate: Candidate, report: EvalReport) -> Dict[str, bool]:
        """Absorb any record-setting *capability* genes from this candidate.

        The spurious gene is never harvested, and traits from candidates that
        regressed protected tasks are ignored -- we only mine traits that were not
        bought with damage elsewhere.
        """
        improved: Dict[str, bool] = {}
        if report.regression_failures > 0:
            return improved
        for gene in GENES:
            if gene == SHORTCUT_GENE:
                continue
            value = candidate.genome.get(gene, 0.0)
            cur = self.records.get(gene)
            if cur is None or value > cur.value + 1e-9:
                self.records[gene] = TraitRecord(
                    gene=gene,
                    value=value,
                    source_cid=candidate.cid,
                    source_origin=candidate.origin,
                )
                improved[gene] = True
        return improved

    def best_genome(self, base: Genome) -> Genome:
        """Recombine the best-known capability genes onto a base genome."""
        out = dict(base)
        for gene, rec in self.records.items():
            out[gene] = max(out.get(gene, 0.0), rec.value)
        out[SHORTCUT_GENE] = base.get(SHORTCUT_GENE, 0.0)
        return out

    def get(self, gene: str) -> float:
        rec = self.records.get(gene)
        return rec.value if rec else 0.0
