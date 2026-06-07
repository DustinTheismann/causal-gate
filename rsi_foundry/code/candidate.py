"""A real code candidate: a hole-filling, the source it renders, and a causal claim.

The causal claim names the single hole the candidate asserts is responsible for its
improvement. The causal-by-revert gate (see ``evaluation.py``) tests that claim by
reverting exactly that hole and re-running the real tests -- if the gain survives,
the claim is false.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from .tasks import SketchTask


@dataclass
class CodeCandidate:
    cid: str
    task: SketchTask
    assignment: Dict[str, str]          # full hole filling
    parent_assignment: Dict[str, str]
    changed_holes: Tuple[str, ...]
    claim_hole: str                     # the hole claimed to carry the gain
    origin: str
    generation: int = 0
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return self.task.render(self.assignment)

    def reverted(self, hole: str) -> Dict[str, str]:
        """The assignment with ``hole`` reset to its parent value (ablation)."""
        out = dict(self.assignment)
        out[hole] = self.parent_assignment.get(hole, self.task.seed.get(hole))
        return out
