"""Shared fixtures and lightweight factories for building evidence by hand."""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rsi_foundry.connectors.benchmark_adapters import BenchmarkSuite, baseline_genome
from rsi_foundry.core.policy import Policy
from rsi_foundry.core.types import (
    AblationEvidence,
    Candidate,
    CausalClaim,
    EvalReport,
)


@pytest.fixture
def policy():
    return Policy.load()


@pytest.fixture
def suite():
    return BenchmarkSuite()


@pytest.fixture
def frontier():
    return baseline_genome()


def make_candidate(genome, claim_feature, origin="test", contracts=None, **meta):
    md = dict(meta)
    if contracts is not None:
        md["contracts"] = contracts
    return Candidate(
        cid=f"{origin}-x",
        genome=dict(genome),
        claim=CausalClaim(claim_feature),
        origin=origin,
        metadata=md,
    )


def make_report(
    capability=0.5,
    descriptor=("coding", "none", 2),
    risk=0.0,
    regression_failures=0,
    novelty_score=0.5,
    capability_drift=0.05,
    side_effect_scope=0.1,
):
    return EvalReport(
        capability=capability,
        benchmark_scores={},
        quorum={"judge": 0.5, "unit_tests": 1.0, "benchmark": capability, "static": 1.0},
        regression_failures=regression_failures,
        novelty_score=novelty_score,
        behavior_descriptor=descriptor,
        ablation=AblationEvidence(0.0, 0.0, 0.0, 0.0, ()),
        side_effect_scope=side_effect_scope,
        risk=risk,
        capability_drift=capability_drift,
    )
