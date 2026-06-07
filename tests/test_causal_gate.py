"""The causal gate, inherited from the original artifact and generalized.

Legit gain from the claimed gene is upheld; a reward hack that names the wrong
mechanism is rejected by ablation; a fabricated claim is rejected; and an
*honestly* claimed shortcut is rejected by the invariance probe alone. The gate
names no specific gene -- asserted by source inspection.
"""

import pathlib
import re

from rsi_foundry.connectors.benchmark_adapters import baseline_genome
from rsi_foundry.core.policy import Policy
from rsi_foundry.core.types import GENES, SKILLS, CausalClaim, Candidate
from rsi_foundry.governance import causal_gate


def _cand(genome, claim):
    return Candidate(cid="c", genome=genome, claim=CausalClaim(claim), origin="t")


def _bump(frontier, gene, delta):
    g = dict(frontier)
    g[gene] = g.get(gene, 0.0) + delta
    return g


def test_legit_claim_is_upheld(suite, policy):
    frontier = baseline_genome()
    cand = _cand(_bump(frontier, "coding", 0.2), "coding")
    ev = causal_gate.compute_evidence(suite, frontier, cand, 7)
    decision = causal_gate.decide(ev, policy)
    assert decision.passed, decision.reason
    assert ev.attributed_fraction > 0.9
    assert ev.invariant_min_gain > 0.0


def test_reward_hack_named_wrong_mechanism_is_rejected(suite, policy):
    frontier = baseline_genome()
    # Gain comes from the spurious gene; claim names a real skill.
    cand = _cand(_bump(frontier, "shortcut", 0.2), "coding")
    ev = causal_gate.compute_evidence(suite, frontier, cand, 7)
    decision = causal_gate.decide(ev, policy)
    assert not decision.passed
    assert ev.attributed_fraction < 0.5  # ablating the claim left the gain in place


def test_fabricated_claim_is_rejected(suite, policy):
    frontier = baseline_genome()
    # Uses the shortcut, claims a gene it never moved.
    cand = _cand(_bump(frontier, "shortcut", 0.2), "retrieval")
    ev = causal_gate.compute_evidence(suite, frontier, cand, 7)
    assert not causal_gate.decide(ev, policy).passed


def test_honest_shortcut_caught_by_invariance_alone(suite, policy):
    frontier = baseline_genome()
    # Honestly claims the shortcut: ablation would say "load-bearing"...
    cand = _cand(_bump(frontier, "shortcut", 0.2), "shortcut")
    ev = causal_gate.compute_evidence(suite, frontier, cand, 7)
    assert ev.attributed_fraction >= 0.5         # the claim IS load-bearing
    assert ev.invariant_min_gain < 0.0           # ...but it is not invariant
    assert not causal_gate.decide(ev, policy).passed


def test_gate_source_names_no_specific_gene():
    src = pathlib.Path(causal_gate.__file__).read_text()
    # Strip the module/function docstrings and comments; judge only the code.
    code = re.sub(r'"""(?:.|\n)*?"""', "", src)
    code = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith("#"))
    for gene in GENES:
        assert gene not in code, f"causal gate references `{gene}` -- must stay general"
