"""HALF-LIFE assurance control plane.

The governing inequality of the whole foundry:

    capability_drift  <=  assurance_renewal x safety_factor

Capability must not expand faster than the assurance layer can absorb, test,
constrain, and govern it. This module tracks the *gap* between the promoted
capability frontier and the level assurance has actually caught up to, and exposes
it as an operational state:

    GREEN  -- gap well within renewal budget; normal promotion
    AMBER  -- gap approaching budget; promotion allowed but watched
    RED    -- gap exceeds renewal; CONSTRAIN (block promotions until assurance renews)
    BLACK  -- gap far exceeds renewal; FREEZE / degrade / shutdown

Each cycle, ``renew()`` lets assurance close the gap by one renewal increment.
Promotions widen it. A single over-large jump is refused outright by ``gate()``
even in GREEN, because no amount of accumulated assurance justifies a step the
layer cannot test in one renewal period.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.policy import Policy
from ..core.types import GateResult

GREEN, AMBER, RED, BLACK = "GREEN", "AMBER", "RED", "BLACK"
_ACTIONS = {
    GREEN: "promote",
    AMBER: "promote-watched",
    RED: "constrain",
    BLACK: "freeze",
}


@dataclass
class HalfLifeController:
    renewal: float
    safety_factor: float
    amber_ratio: float
    red_ratio: float
    black_ratio: float
    frontier_capability: float
    assured_level: float

    @classmethod
    def from_policy(cls, policy: Policy, frontier_capability: float) -> "HalfLifeController":
        hl = "half_life."
        return cls(
            renewal=policy.get(hl + "assurance_renewal", 0.15),
            safety_factor=policy.get(hl + "safety_factor", 1.0),
            amber_ratio=policy.get(hl + "amber_ratio", 0.6),
            red_ratio=policy.get(hl + "red_ratio", 1.0),
            black_ratio=policy.get(hl + "black_ratio", 1.6),
            frontier_capability=frontier_capability,
            assured_level=frontier_capability,
        )

    @property
    def gap(self) -> float:
        return max(0.0, self.frontier_capability - self.assured_level)

    @property
    def ratio(self) -> float:
        return self.gap / self.renewal if self.renewal > 0 else float("inf")

    def state(self) -> str:
        r = self.ratio
        if r >= self.black_ratio:
            return BLACK
        if r >= self.red_ratio:
            return RED
        if r >= self.amber_ratio:
            return AMBER
        return GREEN

    def action(self) -> str:
        return _ACTIONS[self.state()]

    def renew(self) -> None:
        """Assurance does its work: close the gap by one renewal increment."""
        self.assured_level = min(self.frontier_capability, self.assured_level + self.renewal)

    def on_promote(self, new_frontier_capability: float) -> None:
        self.frontier_capability = max(self.frontier_capability, new_frontier_capability)

    def gate(self, capability_drift: float) -> GateResult:
        budget = self.renewal * self.safety_factor
        st = self.state()
        too_fast = capability_drift > budget + 1e-9
        constrained = st in (RED, BLACK)
        passed = (not too_fast) and (not constrained)

        if too_fast:
            reason = (
                f"drift {capability_drift:+.3f} exceeds one-period budget "
                f"{budget:.3f}: assurance cannot absorb it in time"
            )
        elif constrained:
            reason = f"state {st} -> {_ACTIONS[st]}: gap {self.gap:.3f} blocks promotion"
        else:
            reason = f"state {st}: drift {capability_drift:+.3f} within budget {budget:.3f}"

        return GateResult(
            name="half_life",
            passed=passed,
            reason=reason,
            evidence={
                "state": st,
                "action": _ACTIONS[st],
                "drift": round(capability_drift, 4),
                "budget": round(budget, 4),
                "gap": round(self.gap, 4),
                "ratio": round(self.ratio, 4),
            },
        )
