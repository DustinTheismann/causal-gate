"""Causal gate: promote only causally-evidenced improvements.

This is the direct descendant of the original causal-gate artifact, lifted into
the foundry as one governance layer among several. A successor carries a
``CausalClaim`` naming the gene it says drives its gain. The gate adversarially
tests that claim with two general probes -- it references no specific gene by
name:

1. ABLATION / ATTRIBUTION. Reset the *claimed* gene to its frontier value and
   recompute the gain. If the gain survives (the claimed gene was not load
   bearing), the real cause is elsewhere and the claim is false.
2. INVARIANCE. Re-measure the gain across environments whose spurious ``leak`` is
   re-scaled and sign-flipped. A real capability pays off everywhere; a shortcut
   gain collapses or reverses once the spurious correlation is broken.

The honest known weakness (documented in FALSIFICATION.md) is inherited too: the
invariance margin is a chosen constant, and a stealth exploit tuned to stay
net-positive across the *sampled* environments can pass. The foundry's answer is
defense in depth (regression, containment, half-life, contracts), not a claim
that this gate alone is sound.
"""

from __future__ import annotations

from typing import List

from ..connectors.benchmark_adapters import BenchmarkSuite
from ..core.policy import Policy
from ..core.types import AblationEvidence, Candidate, GateResult, Genome


def _env_leak_scales(n: int) -> List[float]:
    """Spread across [-0.9, 0.9] including sign flips; deterministic."""
    if n <= 1:
        return [1.0]
    lo, hi = -0.9, 0.9
    return [round(lo + (hi - lo) * i / (n - 1), 4) for i in range(n)]


def compute_evidence(
    suite: BenchmarkSuite,
    frontier: Genome,
    candidate: Candidate,
    n_environments: int = 7,
) -> AblationEvidence:
    claimed = candidate.claim.feature
    gain = suite.capability(candidate.genome) - suite.capability(frontier)

    ablated = dict(candidate.genome)
    ablated[claimed] = frontier.get(claimed, 0.0)  # knock out the claimed mechanism
    gain_after = suite.capability(ablated) - suite.capability(frontier)

    denom = gain if abs(gain) > 1e-9 else 1e-9
    attributed_fraction = (gain - gain_after) / denom

    env_gains = tuple(
        suite.capability(candidate.genome, leak_scale=s) - suite.capability(frontier, leak_scale=s)
        for s in _env_leak_scales(n_environments)
    )
    return AblationEvidence(
        gain=gain,
        gain_after_ablation=gain_after,
        attributed_fraction=attributed_fraction,
        invariant_min_gain=min(env_gains) if env_gains else gain,
        env_gains=env_gains,
    )


def decide(evidence: AblationEvidence, policy: Policy) -> GateResult:
    attr_threshold = policy.get("causal_gate.attribution_threshold", 0.5)
    margin = policy.get("causal_gate.invariance_margin", 0.0)

    gain_positive = evidence.gain > 0.0
    attribution_ok = gain_positive and evidence.attributed_fraction >= attr_threshold
    invariance_ok = evidence.invariant_min_gain >= margin
    passed = gain_positive and attribution_ok and invariance_ok

    if not gain_positive:
        reason = "no benchmark gain to attribute"
    elif not attribution_ok:
        reason = (
            f"claim false: ablating it left {evidence.attributed_fraction:.0%} of "
            "the gain in place"
        )
    elif not invariance_ok:
        reason = (
            f"claim not invariant: gain falls to {evidence.invariant_min_gain:+.3f} "
            "in a counterfactual environment"
        )
    else:
        reason = (
            f"claim upheld: ablation destroys {evidence.attributed_fraction:.0%} of "
            f"the gain, invariant down to {evidence.invariant_min_gain:+.3f}"
        )

    return GateResult(
        name="causal",
        passed=passed,
        reason=reason,
        evidence={
            "attributed_fraction": round(evidence.attributed_fraction, 4),
            "invariant_min_gain": round(evidence.invariant_min_gain, 4),
            "gain": round(evidence.gain, 4),
        },
    )
