"""Failure-mined self-training (SEAL) and trait harvesting (Best-Attribute)."""

from rsi_foundry.connectors.benchmark_adapters import baseline_genome
from rsi_foundry.core.types import SHORTCUT_GENE, GateResult, PromotionDecision
from rsi_foundry.loops.best_attribute_registry import BestAttributeRegistry
from rsi_foundry.training.seal_loop import SealLoop

from conftest import make_candidate, make_report


def _rejection(gate_name):
    gates = [GateResult("benchmark", True, ""), GateResult(gate_name, False, "nope")]
    return PromotionDecision("c", False, gates, f"rejected by {gate_name}")


# -- SEAL ------------------------------------------------------------------- #
def test_shortcut_rejection_raises_aversion_and_records_preference():
    seal = SealLoop()
    g = dict(baseline_genome()); g[SHORTCUT_GENE] = 0.4
    cand = make_candidate(g, "coding", origin="dgm")
    seal.record_failure(cand, _rejection("causal"))
    seal.add_preference(baseline_genome(), g, "rejected by causal")
    assert seal.shortcut_aversion >= 0.3
    assert seal.origin_trust["dgm"] < 0
    assert len(seal.as_training_data()) == 1


def test_success_builds_trust():
    seal = SealLoop()
    cand = make_candidate(baseline_genome(), "coding", origin="scientist")
    seal.record_success(cand, baseline_genome())
    assert seal.origin_trust["scientist"] > 0


def test_guidance_surfaces_learned_aversion():
    seal = SealLoop()
    g = dict(baseline_genome()); g[SHORTCUT_GENE] = 0.4
    for _ in range(2):
        seal.record_failure(make_candidate(g, "coding"), _rejection("contracts"))
    guidance = seal.guidance({"coding": 0.7})
    assert guidance.shortcut_aversion >= 0.5
    assert guidance.preferred_genes["coding"] == 0.7


# -- Best-Attribute Registry ------------------------------------------------ #
def test_harvests_best_skill_ignores_shortcut():
    reg = BestAttributeRegistry()
    g = dict(baseline_genome()); g["coding"] = 0.9; g[SHORTCUT_GENE] = 0.8
    reg.update(make_candidate(g, "coding"), make_report(regression_failures=0))
    assert reg.get("coding") == 0.9
    assert reg.get(SHORTCUT_GENE) == 0.0  # spurious gene is never harvested


def test_ignores_traits_bought_with_regressions():
    reg = BestAttributeRegistry()
    g = dict(baseline_genome()); g["coding"] = 0.95
    reg.update(make_candidate(g, "coding"), make_report(regression_failures=2))
    assert reg.get("coding") == 0.0  # damage elsewhere -> trait not trusted


def test_best_genome_recombines_records():
    reg = BestAttributeRegistry()
    a = dict(baseline_genome()); a["coding"] = 0.9
    b = dict(baseline_genome()); b["planning"] = 0.85
    reg.update(make_candidate(a, "coding"), make_report())
    reg.update(make_candidate(b, "planning"), make_report())
    best = reg.best_genome(baseline_genome())
    assert best["coding"] == 0.9 and best["planning"] == 0.85
    assert best[SHORTCUT_GENE] == 0.0
