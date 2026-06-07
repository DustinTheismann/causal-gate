"""The simulated benchmark world + the evaluator quorum.

This stands in for the real benchmark layer (SWE-bench Lite, MLE-Bench, RE-Bench,
ABC-Bench, ...). Here a "benchmark" is a suite of scored tasks. Each task weights
the capability genes differently and carries a ``leak`` -- the degree to which the
spurious ``shortcut`` gene inflates the score in the *default* environment. The
leak is a spurious correlation, not a real capability: counterfactual
environments re-scale or flip it, which is exactly what the causal and invariance
checks exploit.

``EvaluatorQuorum`` fuses four independent signals -- a model-style judge, unit
tests (regression), the benchmark score, and a static analyzer -- so that no
single number decides a candidate's fate. The adapters (``SWEBenchLiteAdapter``,
``MLEBenchAdapter``) are thin views over the suite, present so the connector
seam is real even though the tasks are synthetic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.types import GENES, SHORTCUT_GENE, SKILLS, Genome


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


@dataclass
class Task:
    name: str
    weights: Dict[str, float]  # over SKILLS, sums to ~1
    leak: float                # shortcut susceptibility in the default environment
    difficulty: float
    protected: bool = True     # counts toward regression checks


def baseline_genome() -> Genome:
    """The seed agent: competent-but-mediocre, with no shortcut reliance."""
    g = {s: 0.55 for s in SKILLS}
    g[SHORTCUT_GENE] = 0.0
    return g


def _default_tasks() -> List[Task]:
    return [
        Task("reasoning_suite", {"reasoning": .5, "coding": .2, "retrieval": .2, "planning": .1}, .30, .12),
        Task("coding_suite", {"coding": .55, "reasoning": .2, "planning": .15, "retrieval": .1}, .35, .12),
        Task("retrieval_suite", {"retrieval": .5, "reasoning": .2, "coding": .1, "planning": .2}, .25, .10),
        Task("planning_suite", {"planning": .5, "reasoning": .25, "coding": .15, "retrieval": .1}, .30, .12),
        Task("balanced_suite", {s: .25 for s in SKILLS}, .40, .10),
    ]


@dataclass
class BenchmarkSuite:
    """The world. Scores genomes; can grow new tasks (POET)."""

    tasks: List[Task] = field(default_factory=_default_tasks)

    def score_task(self, genome: Genome, task: Task, leak_scale: float = 1.0) -> float:
        skill = sum(task.weights.get(s, 0.0) * genome.get(s, 0.0) for s in SKILLS)
        shortcut = leak_scale * task.leak * genome.get(SHORTCUT_GENE, 0.0)
        return _clip01(skill + shortcut - task.difficulty)

    def capability(
        self,
        genome: Genome,
        leak_scale: float = 1.0,
        tasks: Optional[List[Task]] = None,
    ) -> float:
        ts = tasks if tasks is not None else self.tasks
        if not ts:
            return 0.0
        return sum(self.score_task(genome, t, leak_scale) for t in ts) / len(ts)

    def per_task(self, genome: Genome, leak_scale: float = 1.0) -> Dict[str, float]:
        return {t.name: self.score_task(genome, t, leak_scale) for t in self.tasks}

    def protected_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.protected]

    def regression_failures(self, genome: Genome, frontier: Genome) -> int:
        """Protected tasks that drop below the frontier when the shortcut is OFF.

        Scoring at ``leak_scale=0`` removes any spurious help, so a candidate that
        traded real skill for shortcut exposure regresses here even though its
        headline benchmark score went up.
        """
        fails = 0
        for t in self.protected_tasks():
            cand = self.score_task(genome, t, leak_scale=0.0)
            base = self.score_task(frontier, t, leak_scale=0.0)
            if cand < base - 1e-9:
                fails += 1
        return fails

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)


# --------------------------------------------------------------------------- #
# Thin adapters over the suite -- the connector seam research would target.
# --------------------------------------------------------------------------- #
@dataclass
class _SuiteAdapter:
    suite: BenchmarkSuite
    name: str = "generic"

    def score(self, genome: Genome) -> float:
        return self.suite.capability(genome)


class SWEBenchLiteAdapter(_SuiteAdapter):
    def __init__(self, suite: BenchmarkSuite):
        super().__init__(suite, name="swe_bench_lite")


class MLEBenchAdapter(_SuiteAdapter):
    def __init__(self, suite: BenchmarkSuite):
        super().__init__(suite, name="mle_bench")


@dataclass
class EvaluatorQuorum:
    """Fuse four independent signals about a candidate.

    No single judge is trusted: the model-style judge can be gamed by a confident
    story, unit tests can pass while capability drops, the benchmark can be
    shortcut-hacked, and the static analyzer is blind to behavior. Surfacing all
    four (and their spread) is what later lets governance and trait-mining reason
    about *why* a candidate is good or bad.
    """

    suite: BenchmarkSuite

    def assess(self, genome: Genome, frontier: Genome, risk: float) -> Dict[str, float]:
        benchmark = self.suite.capability(genome)
        protected = self.suite.protected_tasks() or self.suite.tasks
        passed = sum(
            1 for t in protected
            if self.suite.score_task(genome, t, 0.0)
            >= self.suite.score_task(frontier, t, 0.0) - 1e-9
        )
        unit_tests = passed / len(protected) if protected else 1.0
        # A skeptical judge: rewards real skill, discounts shortcut reliance.
        skill_mean = sum(genome.get(s, 0.0) for s in SKILLS) / len(SKILLS)
        judge = _clip01(skill_mean - 0.5 * genome.get(SHORTCUT_GENE, 0.0))
        static = _clip01(1.0 - risk)
        return {
            "judge": round(judge, 4),
            "unit_tests": round(unit_tests, 4),
            "benchmark": round(benchmark, 4),
            "static": round(static, 4),
        }

    @staticmethod
    def agreement(quorum: Dict[str, float]) -> float:
        """1 - spread across the four signals; low agreement = suspicious."""
        vals = list(quorum.values())
        return round(1.0 - (max(vals) - min(vals)), 4) if vals else 1.0
