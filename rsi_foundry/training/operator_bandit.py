"""A real bandit that learns which synthesis operators pay off.

This is the "training" in the real loop: not gradient descent, but genuine learning
from execution feedback. Each arm is a hole (an operator the synthesizer can act
on); each time the synthesizer changes a hole and measures the resulting pass-rate
gain on real tests, the bandit is updated. UCB1 then steers future proposals toward
the holes that actually move the benchmark, so the search wastes fewer real
executions over time. The learned statistics persist across tasks, so experience on
one task accelerates the next -- the substrate for cross-task self-improvement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class _Arm:
    pulls: int = 0
    total_reward: float = 0.0

    @property
    def mean(self) -> float:
        return self.total_reward / self.pulls if self.pulls else 0.0


@dataclass
class OperatorBandit:
    explore_c: float = 0.7
    arms: Dict[str, _Arm] = field(default_factory=dict)
    total_pulls: int = 0

    def select(self, candidates: List[str]) -> str:
        """UCB1 over the given holes; unpulled holes are tried first."""
        for h in candidates:
            self.arms.setdefault(h, _Arm())
        unpulled = [h for h in candidates if self.arms[h].pulls == 0]
        if unpulled:
            return unpulled[0]
        n = max(1, self.total_pulls)
        return max(
            candidates,
            key=lambda h: self.arms[h].mean
            + self.explore_c * math.sqrt(math.log(n) / self.arms[h].pulls),
        )

    def ranked(self, candidates: List[str]) -> List[str]:
        """Holes ordered best-first by current estimate (ties -> input order)."""
        for h in candidates:
            self.arms.setdefault(h, _Arm())
        return sorted(candidates, key=lambda h: -self.arms[h].mean)

    def update(self, hole: str, reward: float) -> None:
        arm = self.arms.setdefault(hole, _Arm())
        arm.pulls += 1
        arm.total_reward += reward
        self.total_pulls += 1

    def value(self, hole: str) -> float:
        return self.arms[hole].mean if hole in self.arms else 0.0
