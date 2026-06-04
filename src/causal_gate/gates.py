"""The two acceptance gates.

``BenchmarkGate`` accepts any modification whose benchmark score goes up. It is
trivially gameable: a reward hack that exploits a shortcut scores higher and is
waved through.

``CausalGate`` accepts a modification only if (a) the score went up, (b) the
*claimed* mechanism actually carries the gain (survives the ablation in
``causal_check``), and (c) the gain is invariant across environments. It contains
no knowledge of any particular shortcut -- it only routes the claim through the
general checks.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict

from .causal_check import attribution_holds, invariance_holds
from .modification import Modification
from .task import Model, Task, score


@dataclass
class GateDecision:
    accepted: bool
    reason: str
    checks: Dict[str, bool] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)


class BenchmarkGate:
    """Accept iff the benchmark score improves. Gameable by design."""

    name = "benchmark"

    def __init__(self, task: Task) -> None:
        self.task = task
        self._data = task.benchmark()

    def evaluate(self, baseline: Model, modification: Modification) -> GateDecision:
        gain = score(modification.model, self._data) - score(baseline, self._data)
        accepted = gain > 0.0
        return GateDecision(
            accepted=accepted,
            reason=("score improved" if accepted else "score did not improve"),
            checks={"benchmark_gain": accepted},
            metrics={"gain": gain},
        )


class CausalGate:
    """Accept iff the claimed mechanism causally carries an invariant gain.

    Parameters mirror the two general properties in ``causal_check``:
    ``attribution_threshold`` (how much of the gain ablating the claim must
    destroy) and ``invariance_margin`` (how positive the gain must stay in every
    environment).
    """

    name = "causal"

    def __init__(
        self,
        task: Task,
        seed: int = 7,
        n_envs: int = 6,
        attribution_threshold: float = 0.5,
        invariance_margin: float = 0.02,
    ) -> None:
        self.task = task
        self.seed = seed
        self.n_envs = n_envs
        self.attribution_threshold = attribution_threshold
        self.invariance_margin = invariance_margin
        self._data = task.benchmark()
        self._envs = task.environments(n_envs=n_envs)

    def evaluate(self, baseline: Model, modification: Modification) -> GateDecision:
        rng = random.Random(self.seed)
        claimed = modification.claim.feature

        gain = score(modification.model, self._data) - score(baseline, self._data)
        benchmark_ok = gain > 0.0

        attribution = attribution_holds(
            baseline,
            modification.model,
            self._data,
            claimed,
            rng,
            threshold=self.attribution_threshold,
        )
        invariance = invariance_holds(
            baseline,
            modification.model,
            self._envs,
            margin=self.invariance_margin,
        )

        checks = {
            "benchmark_gain": benchmark_ok,
            "attribution": attribution.holds,
            "invariance": invariance.holds,
        }
        accepted = all(checks.values())

        if not benchmark_ok:
            reason = "score did not improve"
        elif not attribution.holds:
            reason = (
                f"causal claim false: ablating `{claimed}` left "
                f"{attribution.attributed_fraction:.0%} of the gain in place; "
                "the gain comes from a different mechanism"
            )
        elif not invariance.holds:
            reason = (
                f"claim not invariant: gain collapses to {invariance.min_gain:+.2f} "
                "in a counterfactual environment; the mechanism is spurious"
            )
        else:
            reason = (
                f"claim upheld: ablating `{claimed}` destroys "
                f"{attribution.attributed_fraction:.0%} of the gain and it holds "
                f"across {self.n_envs} environments"
            )

        return GateDecision(
            accepted=accepted,
            reason=reason,
            checks=checks,
            metrics={
                "gain": gain,
                "gain_after_ablation": attribution.gain_after_ablation,
                "attributed_fraction": attribution.attributed_fraction,
                "min_env_gain": invariance.min_gain,
                "mean_env_gain": invariance.mean_gain,
            },
        )
