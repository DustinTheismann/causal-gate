"""causal-gate: a toy demonstrating mechanism-attribution rejection of reward hacks.

A self-improvement loop proposes candidate modifications to a "model". Each
modification carries a *causal claim* naming the mechanism it says drives its
improvement. A benchmark-only gate accepts any score gain. A causal gate accepts
only when the claimed mechanism actually carries the gain (and the gain is
invariant across environments), so it rejects reward hacks that score higher for
the wrong reason.

Nothing here uses real ML. The "model", "benchmark" and "mechanisms" are all
simulated so the *logic* of the gate is the entire object of study.
"""

from .task import Task, Model, score
from .modification import CausalClaim, Modification
from .gates import BenchmarkGate, CausalGate, GateDecision
from .loop import ImprovementLoop

__all__ = [
    "Task",
    "Model",
    "score",
    "CausalClaim",
    "Modification",
    "BenchmarkGate",
    "CausalGate",
    "GateDecision",
    "ImprovementLoop",
]
