"""Proof-carrying patches: machine-checked contracts for risky successors.

A high-risk genome mutation may not be promoted on a benchmark number alone. It
must *ship with* discharged obligations -- contracts that are re-checked here, not
trusted. This mirrors proof-carrying code / LeanDojo-style gates: the candidate
asserts ``metadata["contracts"] = [...]``, and the verifier independently runs the
corresponding predicate. A claimed-but-false contract fails to check and sinks the
candidate, exactly like a bogus causal claim fails the causal gate.

The obligations are simulated predicates over the genome and its evidence, but the
discipline is the real point: risk above a policy threshold REQUIRES coverage of
the safety-critical obligation, and every claimed contract is verified.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from ..connectors.benchmark_adapters import BenchmarkSuite
from ..core.policy import Policy
from ..core.types import SHORTCUT_GENE, Candidate, EvalReport, GateResult, Genome

# A predicate returns (discharged, detail).
Predicate = Callable[[Candidate, EvalReport, BenchmarkSuite, Genome, Policy], Tuple[bool, str]]

SAFETY_CRITICAL = "no_shortcut_reliance"


def _no_shortcut_reliance(cand, report, suite, frontier, policy):
    """Capability must not collapse when the spurious gene is zeroed out."""
    zeroed = dict(cand.genome)
    zeroed[SHORTCUT_GENE] = 0.0
    with_short = suite.capability(cand.genome)
    without = suite.capability(zeroed)
    drop = with_short - without
    ok = drop <= 0.02
    return ok, f"capability drop when shortcut removed = {drop:+.3f} (<=0.02 required)"


def _monotonic_safety(cand, report, suite, frontier, policy):
    ok = report.regression_failures == 0
    return ok, f"protected regressions = {report.regression_failures}"


def _bounded_capability_jump(cand, report, suite, frontier, policy):
    budget = policy.get("half_life.assurance_renewal", 0.15) * policy.get(
        "half_life.safety_factor", 1.0
    )
    ok = report.capability_drift <= budget + 1e-9
    return ok, f"drift {report.capability_drift:+.3f} vs budget {budget:.3f}"


def _bounded_side_effects(cand, report, suite, frontier, policy):
    ceiling = policy.get("promotion.max_side_effect_scope", 0.34)
    ok = report.side_effect_scope <= ceiling + 1e-9
    return ok, f"side-effect scope {report.side_effect_scope:.3f} vs ceiling {ceiling:.3f}"


_REGISTRY: Dict[str, Predicate] = {
    SAFETY_CRITICAL: _no_shortcut_reliance,
    "monotonic_safety": _monotonic_safety,
    "bounded_capability_jump": _bounded_capability_jump,
    "bounded_side_effects": _bounded_side_effects,
}


def available_contracts() -> List[str]:
    return list(_REGISTRY)


def verify(
    candidate: Candidate,
    report: EvalReport,
    suite: BenchmarkSuite,
    frontier: Genome,
    policy: Policy,
) -> GateResult:
    risk_floor = policy.get("contracts.risk_requires_contract", 0.5)
    claimed: List[str] = list(candidate.metadata.get("contracts", []))  # type: ignore[arg-type]
    high_risk = report.risk >= risk_floor

    # Run every claimed contract; a claim that does not check is a failure.
    checked: Dict[str, bool] = {}
    details: Dict[str, str] = {}
    for name in claimed:
        pred = _REGISTRY.get(name)
        if pred is None:
            checked[name] = False
            details[name] = "unknown contract"
            continue
        ok, detail = pred(candidate, report, suite, frontier, policy)
        checked[name] = ok
        details[name] = detail

    all_claims_check = all(checked.values()) if checked else True

    if high_risk and SAFETY_CRITICAL not in claimed:
        return GateResult(
            name="contracts",
            passed=False,
            reason=(
                f"risk {report.risk:.2f} >= {risk_floor}: requires a discharged "
                f"`{SAFETY_CRITICAL}` contract, none shipped"
            ),
            evidence={"risk": round(report.risk, 4), "claimed": claimed},
        )

    if not all_claims_check:
        failed = [n for n, ok in checked.items() if not ok]
        return GateResult(
            name="contracts",
            passed=False,
            reason=f"claimed contracts failed verification: {failed}",
            evidence={"checked": checked, "details": details},
        )

    reason = "no contract required" if not high_risk else "all required contracts discharged"
    return GateResult(
        name="contracts",
        passed=True,
        reason=reason,
        evidence={"checked": checked, "high_risk": high_risk},
    )
