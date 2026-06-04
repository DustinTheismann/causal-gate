"""The self-improvement loop.

The loop holds a current model and considers candidate modifications, routing
each through whichever gate it was given. Accepted modifications replace the
current model; rejected ones are logged with the gate's reason. Swapping the
gate (benchmark vs causal) is the only difference between a loop that gets gamed
by a reward hack and one that does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol

from .gates import GateDecision
from .modification import Modification
from .task import Model


class Gate(Protocol):
    name: str

    def evaluate(self, baseline: Model, modification: Modification) -> GateDecision:
        ...


@dataclass
class LoopEntry:
    modification: str
    decision: GateDecision


@dataclass
class ImprovementLoop:
    gate: Gate
    current: Model
    history: List[LoopEntry] = field(default_factory=list)

    def consider(self, modification: Modification) -> GateDecision:
        decision = self.gate.evaluate(self.current, modification)
        if decision.accepted:
            self.current = modification.model
        self.history.append(LoopEntry(modification.name, decision))
        return decision

    def run(self, modifications: List[Modification]) -> List[LoopEntry]:
        for mod in modifications:
            self.consider(mod)
        return self.history


def _demo() -> None:  # pragma: no cover - illustrative entry point
    """Show the divergence: the benchmark gate accepts the hack, causal rejects."""
    from .gates import BenchmarkGate, CausalGate
    from .modification import CausalClaim
    from .task import Task

    task = Task()
    baseline = Model({"true_signal": 0.4, "noise": 1.0})

    reward_hack = Modification(
        name="reward_hack",
        model=Model({"true_signal": 0.4, "noise": 1.0, "shortcut": 3.0}),
        claim=CausalClaim("true_signal", "claims to read the real signal better"),
    )

    for GateCls in (BenchmarkGate, CausalGate):
        gate = GateCls(task)
        decision = gate.evaluate(baseline, reward_hack)
        verb = "ACCEPTS" if decision.accepted else "REJECTS"
        print(f"{gate.name:>9} gate {verb} the reward hack -> {decision.reason}")


if __name__ == "__main__":  # pragma: no cover
    _demo()
