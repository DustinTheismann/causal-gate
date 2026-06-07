"""POET-style environment coevolution.

Agents and environments improve together. When the capability frontier has
mastered the current suite (mean score above a policy threshold), POET spawns a
new, harder task -- a fresh weight mix and higher difficulty -- so the population
faces an open-ended, non-stationary benchmark instead of a fixed target it can
overfit. New environments are also fresh ground for the causal/invariance checks.
"""

from __future__ import annotations

import random
from typing import List

from ..connectors.benchmark_adapters import BenchmarkSuite, Task
from ..core.policy import Policy
from ..core.types import SKILLS, Genome


def coevolve(
    suite: BenchmarkSuite,
    frontier: Genome,
    rng: random.Random,
    policy: Policy,
) -> List[str]:
    """Maybe spawn a harder task; return the names of any new environments."""
    spawn_score = policy.get("poet.spawn_score", 0.7)
    max_envs = policy.get("poet.max_environments", 24)
    if len(suite.tasks) >= max_envs:
        return []
    if suite.capability(frontier) < spawn_score:
        return []

    # A new niche: random emphasis, normalized, harder than the current hardest.
    raw = {s: rng.uniform(0.1, 1.0) for s in SKILLS}
    total = sum(raw.values())
    weights = {s: round(v / total, 4) for s, v in raw.items()}
    hardest = max((t.difficulty for t in suite.tasks), default=0.1)
    name = f"poet_{len(suite.tasks)}"
    suite.add_task(
        Task(
            name=name,
            weights=weights,
            leak=round(rng.uniform(0.2, 0.4), 4),
            difficulty=round(min(0.45, hardest + 0.04), 4),
        )
    )
    return [name]
