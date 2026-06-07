"""Real evaluation: memoized test execution + causal-by-revert on executing code.

The ``Evaluator`` runs each distinct source at most once (results are cached) and
counts cache misses as ``evals`` -- a real measure of search cost. The causal probe
is the original causal gate, made concrete on code: it reverts exactly the hole the
candidate *claims* is responsible and re-runs the real tests. If the pass-rate gain
survives reverting the claimed hole, the claim is false; and the gain must also
hold on the held-out split (generalization), so a filling that overfits the visible
cases is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from . import execution
from .candidate import CodeCandidate
from .tasks import SketchTask


@dataclass
class CausalEvidence:
    gain: float
    gain_after_revert: float
    attributed_fraction: float
    gain_held: float
    candidate_visible: float
    contained: bool


class Evaluator:
    def __init__(self, task: SketchTask, timeout: float = 5.0) -> None:
        self.task = task
        self.timeout = timeout
        self._cache: Dict[Tuple[str, str], execution.ExecResult] = {}
        self.evals = 0

    def _run(self, source, tests, tag) -> execution.ExecResult:
        key = (tag, source)
        if key not in self._cache:
            self._cache[key] = execution.run(source, self.task.entry, tests, self.timeout)
            self.evals += 1
        return self._cache[key]

    def visible_result(self, assignment) -> execution.ExecResult:
        return self._run(self.task.render(assignment), self.task.visible, "v")

    def held_result(self, assignment) -> execution.ExecResult:
        return self._run(self.task.render(assignment), self.task.held, "h")

    def visible_rate(self, assignment) -> float:
        return self.visible_result(assignment).pass_rate

    def held_rate(self, assignment) -> float:
        return self.held_result(assignment).pass_rate

    def causal_evidence(self, candidate: CodeCandidate) -> CausalEvidence:
        parent = candidate.parent_assignment
        parent_v = self.visible_rate(parent)
        cand_res = self.visible_result(candidate.assignment)
        gain = cand_res.pass_rate - parent_v

        reverted = candidate.reverted(candidate.claim_hole)
        gain_after = self.visible_rate(reverted) - parent_v

        denom = gain if abs(gain) > 1e-9 else 1e-9
        attributed = (gain - gain_after) / denom
        gain_held = self.held_rate(candidate.assignment) - self.held_rate(parent)

        return CausalEvidence(
            gain=gain,
            gain_after_revert=gain_after,
            attributed_fraction=attributed,
            gain_held=gain_held,
            candidate_visible=cand_res.pass_rate,
            contained=cand_res.ok,
        )

    def passing_visible_indices(self, assignment) -> frozenset:
        return frozenset(i for i, ok in enumerate(self.visible_result(assignment).results) if ok)
