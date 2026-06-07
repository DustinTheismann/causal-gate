"""Recursive R&D Foundry -- a governed recursive self-improvement scaffold.

Generate successors -> sandbox -> benchmark -> prove/test/ablate -> mine traits
and failures -> promote only governed improvements -> coevolve the benchmark ->
repeat. Standard library only; every model/benchmark/sandbox/proof is simulated
so the governance LOGIC is the object of study.
"""

from .core.orchestrator import Foundry
from .core.policy import Policy
from .core.types import Candidate, CausalClaim, CycleReport, EvalReport, GateResult

__all__ = [
    "Foundry",
    "Policy",
    "Candidate",
    "CausalClaim",
    "CycleReport",
    "EvalReport",
    "GateResult",
]
