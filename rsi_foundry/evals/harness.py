"""Evaluation harness: gather every signal about a candidate into one report.

The harness does not judge -- it measures. It runs the benchmark, the evaluator
quorum, the regression check, the behavior-descriptor / novelty computation, the
causal ablation probe, and the risk estimate, and packs them into an
``EvalReport`` for the gates. Keeping measurement and judgement separate is what
lets the same evidence feed promotion, trait-mining, failure-mining, and the
RunPack record without any of them re-deriving it.
"""

from __future__ import annotations

from typing import Tuple

from ..connectors.benchmark_adapters import BenchmarkSuite, EvaluatorQuorum
from ..core.policy import Policy
from ..core.types import (
    SHORTCUT_GENE,
    SKILLS,
    Candidate,
    EvalReport,
    Genome,
)
from ..governance import causal_gate


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def behavior_descriptor(genome: Genome, capability: float) -> Tuple[object, ...]:
    """A MAP-Elites niche key: (dominant skill, shortcut band, capability band)."""
    dominant = max(SKILLS, key=lambda s: genome.get(s, 0.0))
    sc = genome.get(SHORTCUT_GENE, 0.0)
    shortcut_band = "none" if sc < 0.05 else "low" if sc < 0.4 else "high"
    capability_band = int(_clip01(capability) * 5)  # 0..5
    return (dominant, shortcut_band, capability_band)


def estimate_risk(genome: Genome, capability_drift: float, budget: float) -> float:
    """Risk rises with shortcut reliance and with over-fast capability jumps."""
    return round(_clip01(0.8 * genome.get(SHORTCUT_GENE, 0.0) + max(0.0, capability_drift - budget)), 4)


def evaluate(
    candidate: Candidate,
    suite: BenchmarkSuite,
    frontier: Genome,
    archive,  # NoveltyLedger (duck-typed to avoid an import cycle)
    policy: Policy,
    side_effect_scope: float,
) -> EvalReport:
    capability = suite.capability(candidate.genome)
    drift = capability - suite.capability(frontier)
    budget = policy.get("half_life.assurance_renewal", 0.15) * policy.get(
        "half_life.safety_factor", 1.0
    )
    risk = estimate_risk(candidate.genome, drift, budget)

    quorum = EvaluatorQuorum(suite).assess(candidate.genome, frontier, risk)
    descriptor = behavior_descriptor(candidate.genome, capability)
    novelty = archive.novelty(candidate.genome, descriptor)
    evidence = causal_gate.compute_evidence(
        suite, frontier, candidate, n_environments=policy.get("causal_gate.n_environments", 7)
    )

    return EvalReport(
        capability=round(capability, 4),
        benchmark_scores={k: round(v, 4) for k, v in suite.per_task(candidate.genome).items()},
        quorum=quorum,
        regression_failures=suite.regression_failures(candidate.genome, frontier),
        novelty_score=round(novelty, 4),
        behavior_descriptor=descriptor,
        ablation=evidence,
        side_effect_scope=side_effect_scope,
        risk=risk,
        capability_drift=round(drift, 4),
    )
