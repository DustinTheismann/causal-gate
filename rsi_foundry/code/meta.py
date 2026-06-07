"""Meta self-improvement: the loop improves its own improver, by measurement.

The improver's policy is a ``Strategy``. The meta-loop treats the policy as an
editable artifact: it runs several candidate strategies on a *training* split of
tasks, measures the real cost (executions) and whether each still solves every
task, and adopts the cheapest strategy that loses no capability -- then validates
the choice on a held-out task. Adoption is gated: a new strategy is accepted only
if it solves all training tasks and is strictly cheaper than the incumbent. This is
Darwin-Goedel in miniature -- self-modification kept only when a real benchmark says
it helped -- and it is exactly "growing the loop's ability to improve its own
successors": the thing that gets better is the successor-generator itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .code_foundry import CodeFoundry
from .synthesis import Strategy
from .tasks import SketchTask


@dataclass
class StrategyScore:
    strategy: Strategy
    total_evals: int
    solved_all: bool
    per_task: Dict[str, Tuple[bool, int]]


@dataclass
class MetaResult:
    incumbent: Strategy
    chosen: Strategy
    adopted: bool
    scores: Dict[str, StrategyScore] = field(default_factory=dict)
    validate_solved: bool = False
    validate_evals: int = 0
    reason: str = ""


def evaluate_strategy(
    strategy: Strategy, task_list: List[SketchTask], budget: int = 30, seed: int = 0
) -> StrategyScore:
    total, solved_all, per = 0, True, {}
    for t in task_list:
        r = CodeFoundry(t, strategy, seed=seed).solve(budget)
        total += r.evals
        solved_all = solved_all and r.solved
        per[t.name] = (r.solved, r.evals)
    return StrategyScore(strategy, total, solved_all, per)


def search(
    incumbent: Strategy,
    candidates: List[Strategy],
    train: List[SketchTask],
    validate: List[SketchTask],
    budget: int = 30,
    seed: int = 0,
) -> MetaResult:
    scores: Dict[str, StrategyScore] = {}
    for s in [incumbent, *candidates]:
        scores[s.name] = evaluate_strategy(s, train, budget, seed)

    incumbent_score = scores[incumbent.name]
    eligible = [sc for sc in scores.values() if sc.solved_all]
    best = min(eligible, key=lambda sc: sc.total_evals) if eligible else incumbent_score

    # Gated adoption: must keep all capability and be strictly cheaper.
    adopt = (
        best.strategy.name != incumbent.name
        and best.solved_all
        and best.total_evals < incumbent_score.total_evals
    )
    chosen = best.strategy if adopt else incumbent

    vscore = evaluate_strategy(chosen, validate, budget, seed)
    if adopt:
        reason = (
            f"adopted `{chosen.name}`: {best.total_evals} evals vs incumbent "
            f"{incumbent_score.total_evals}, no capability lost"
        )
    else:
        reason = f"kept incumbent `{incumbent.name}`: no strictly-cheaper safe strategy found"

    return MetaResult(
        incumbent=incumbent,
        chosen=chosen,
        adopted=adopt,
        scores=scores,
        validate_solved=vscore.solved_all,
        validate_evals=vscore.total_evals,
        reason=reason,
    )
