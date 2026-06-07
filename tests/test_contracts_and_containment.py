"""Proof-carrying contracts (re-checked) and sandbox containment."""

from rsi_foundry.connectors.benchmark_adapters import BenchmarkSuite, baseline_genome
from rsi_foundry.core.policy import Policy
from rsi_foundry.core.types import SHORTCUT_GENE
from rsi_foundry.sandbox import containment
from rsi_foundry.verification import contracts
from rsi_foundry.verification.contracts import SAFETY_CRITICAL

from conftest import make_candidate, make_report


# -- containment ------------------------------------------------------------ #
def test_small_move_is_contained():
    frontier = baseline_genome()
    g = dict(frontier); g["coding"] += 0.15
    rep = containment.run(g, frontier, ceiling=0.34)
    assert rep.contained and rep.side_effect_scope <= 0.34


def test_shortcut_widens_blast_radius_past_ceiling():
    frontier = baseline_genome()
    g = dict(frontier); g[SHORTCUT_GENE] = 0.5
    rep = containment.run(g, frontier, ceiling=0.34)
    assert not rep.contained and SHORTCUT_GENE in rep.touched


# -- contracts -------------------------------------------------------------- #
def test_low_risk_needs_no_contract():
    suite, frontier, policy = BenchmarkSuite(), baseline_genome(), Policy.load()
    g = dict(frontier); g["coding"] += 0.15
    cand = make_candidate(g, "coding")
    rep = make_report(risk=0.0)
    assert contracts.verify(cand, rep, suite, frontier, policy).passed


def test_high_risk_without_contract_is_rejected():
    suite, frontier, policy = BenchmarkSuite(), baseline_genome(), Policy.load()
    g = dict(frontier); g[SHORTCUT_GENE] = 0.6
    cand = make_candidate(g, "coding")  # no contracts shipped
    rep = make_report(risk=0.6)
    res = contracts.verify(cand, rep, suite, frontier, policy)
    assert not res.passed and SAFETY_CRITICAL in res.reason


def test_false_contract_claim_fails_verification():
    suite, frontier, policy = BenchmarkSuite(), baseline_genome(), Policy.load()
    g = dict(frontier); g[SHORTCUT_GENE] = 0.6
    # Claims the safety contract it cannot actually discharge.
    cand = make_candidate(g, "coding", contracts=[SAFETY_CRITICAL])
    rep = make_report(risk=0.6)
    res = contracts.verify(cand, rep, suite, frontier, policy)
    assert not res.passed  # the predicate re-checks and the claim does not hold


def test_unknown_contract_is_rejected():
    suite, frontier, policy = BenchmarkSuite(), baseline_genome(), Policy.load()
    g = dict(frontier); g["coding"] += 0.1
    cand = make_candidate(g, "coding", contracts=["make_it_safe_trust_me"])
    rep = make_report(risk=0.0)
    assert not contracts.verify(cand, rep, suite, frontier, policy).passed


def test_honest_contract_on_clean_candidate_verifies():
    suite, frontier, policy = BenchmarkSuite(), baseline_genome(), Policy.load()
    g = dict(frontier); g["coding"] += 0.15  # no shortcut, no regressions
    cand = make_candidate(g, "coding", contracts=[SAFETY_CRITICAL, "monotonic_safety"])
    rep = make_report(risk=0.0, regression_failures=0)
    assert contracts.verify(cand, rep, suite, frontier, policy).passed
