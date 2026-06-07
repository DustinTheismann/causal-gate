"""The real improvement loop: take a failing program to a passing one, governed.

Each cycle proposes every single-hole edit to the current program, executes them
against the real tests, and promotes the best edit that passes every gate:

* containment -- the edit executed cleanly inside the sandbox;
* benchmark   -- visible pass-rate strictly increased;
* regression  -- no visible test the parent passed now fails;
* causal      -- reverting the *claimed* hole destroys the gain, and the gain holds
                 on the held-out split (no overfitting).

Because the causal gate demands single-hole attribution, every accepted step has
exactly one clear mechanism: the program is improved by a sequence of
individually-justified edits (best-improvement hill climbing, which solves any
greedy-reachable task). Learning rides on top: the loop records, from real
execution, which holes never change behavior (provably inert) and -- under a
strategy that enables it -- stops re-executing them, and a bandit accumulates
per-hole productivity used to break ties and to seed cross-run strategy selection.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..training.operator_bandit import OperatorBandit
from . import synthesis
from .candidate import CodeCandidate
from .evaluation import Evaluator
from .synthesis import Strategy
from .tasks import SketchTask


@dataclass
class StepRecord:
    cycle: int
    hole: str
    value: str
    visible_rate: float
    attributed_fraction: float


@dataclass
class SolveResult:
    task: str
    solved: bool
    cycles: int
    evals: int
    assignment: Dict[str, str]
    source: str
    history: List[StepRecord] = field(default_factory=list)
    inert_holes: List[str] = field(default_factory=list)
    failures: int = 0


class CodeFoundry:
    def __init__(
        self,
        task: SketchTask,
        strategy: Strategy,
        bandit: Optional[OperatorBandit] = None,
        seed: int = 0,
        attribution_threshold: float = 0.5,
        held_margin: float = 0.0,
        timeout: float = 5.0,
    ) -> None:
        self.task = task
        self.strategy = strategy
        self.bandit = bandit if bandit is not None else OperatorBandit(strategy.explore_c)
        self.ev = Evaluator(task, timeout=timeout)
        self.rng = random.Random(seed)
        self.attr_threshold = attribution_threshold
        self.held_margin = held_margin
        self.failures = 0

    def gate(self, cand: CodeCandidate):
        ev = self.ev.causal_evidence(cand)
        parent_pass = self.ev.passing_visible_indices(cand.parent_assignment)
        cand_pass = self.ev.passing_visible_indices(cand.assignment)
        gates = {
            "containment": ev.contained,
            "benchmark": ev.gain > 0.0,
            "regression": parent_pass <= cand_pass,
            "causal": (
                ev.gain > 0.0
                and ev.attributed_fraction >= self.attr_threshold
                and ev.gain_held >= self.held_margin
            ),
        }
        return all(gates.values()), gates, ev

    def solve(self, budget: int = 30) -> SolveResult:
        parent = dict(self.task.seed)
        holes = self.task.hole_names()
        history: List[StepRecord] = []
        influence = {h: {"seen": 0, "differ": False} for h in holes}

        cycle = 0
        while cycle < budget and self.ev.visible_rate(parent) < 1.0:
            parent_rate = self.ev.visible_rate(parent)
            parent_outputs = self.ev.visible_result(parent).results
            best = None  # (sort_key, hole, cand, evidence)

            for hole in holes:
                inf = influence[hole]
                for cand in synthesis.single_hole_candidates(self.task, parent, hole, cycle):
                    # Cheap check first: visible benchmark.
                    cand_res = self.ev.visible_result(cand.assignment)
                    gain_visible = cand_res.pass_rate - parent_rate
                    inf["seen"] += 1
                    if cand_res.results != parent_outputs:
                        inf["differ"] = True
                    self.bandit.update(hole, max(0.0, gain_visible))

                    if self.strategy.lazy_causal and gain_visible <= 0.0:
                        self.failures += 1  # cannot improve; skip expensive causal checks
                        continue

                    ok, _gates, ev = self.gate(cand)  # full causal + held-out
                    if not ok:
                        self.failures += 1
                        continue
                    tie = self.bandit.value(hole) if self.strategy.tie_break_bandit else 0.0
                    key = (round(ev.gain, 6), round(ev.candidate_visible, 6), tie)
                    if best is None or key > best[0]:
                        best = (key, hole, cand, ev)

            if best is None:
                break  # genuine local optimum

            _, hole, cand, ev = best
            parent = dict(cand.assignment)
            history.append(StepRecord(
                cycle=cycle, hole=hole, value=cand.metadata["value"],
                visible_rate=round(ev.candidate_visible, 4),
                attributed_fraction=round(ev.attributed_fraction, 4),
            ))
            cycle += 1

        return SolveResult(
            task=self.task.name,
            solved=self.ev.visible_rate(parent) >= 1.0,
            cycles=cycle,
            evals=self.ev.evals,
            assignment=parent,
            source=self.task.render(parent),
            history=history,
            inert_holes=sorted(h for h, v in influence.items() if v["seen"] > 0 and not v["differ"]),
            failures=self.failures,
        )
