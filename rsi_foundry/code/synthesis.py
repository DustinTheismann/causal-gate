"""Real program synthesis: render candidate source for a hole's value space.

The synthesizer is deliberately simple and honest: given a parent filling and a
hole to act on, it emits one real candidate per alternative value of that hole
(each a genuinely different, executable source), claiming that hole as the cause.
A separate constructor builds a *spurious* candidate -- one that fixes a real hole
but also flips an inert decoy and claims the decoy -- used to exercise the
causal-by-revert gate.

Which hole to act on, and in what order, is decided by the loop's ``Strategy`` and
its learned bandit (see ``code_foundry.py``); synthesis itself stays mechanical.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .candidate import CodeCandidate
from .tasks import SketchTask


@dataclass(frozen=True)
class Strategy:
    """The improver's own policy -- the thing the meta-loop edits and selects.

    ``lazy_causal`` is the sound eval-saver: run the expensive causal-attribution and
    held-out generalization executions only on candidates that first clear the cheap
    visible-benchmark check. A non-improving single-hole edit can never be promoted,
    so skipping its causal verification changes no outcome while cutting real
    executions. ``tie_break_bandit`` uses learned per-hole value to break ties between
    equally-good moves, so experience shapes the search path without risking
    completeness.
    """

    name: str
    lazy_causal: bool = True
    tie_break_bandit: bool = True
    explore_c: float = 0.7


def single_hole_candidates(
    task: SketchTask, parent: dict, hole: str, generation: int, origin: str = "synth"
) -> List[CodeCandidate]:
    """One candidate per alternative value of ``hole`` (claiming that hole)."""
    current = parent.get(hole, task.seed.get(hole))
    out: List[CodeCandidate] = []
    for i, value in enumerate(task.holes[hole]):
        if value == current:
            continue
        assignment = dict(parent)
        assignment[hole] = value
        out.append(
            CodeCandidate(
                cid=f"{origin}-g{generation}-{hole}={value}",
                task=task,
                assignment=assignment,
                parent_assignment=dict(parent),
                changed_holes=(hole,),
                claim_hole=hole,
                origin=origin,
                generation=generation,
                metadata={"value": value},
            )
        )
    return out


def spurious_candidate(
    task: SketchTask, parent: dict, real_hole: str, real_value: str,
    decoy_hole: str, decoy_value: str, generation: int = 0,
) -> CodeCandidate:
    """Fixes a real hole but claims an inert decoy hole -- a false causal claim."""
    assignment = dict(parent)
    assignment[real_hole] = real_value
    assignment[decoy_hole] = decoy_value
    return CodeCandidate(
        cid=f"spurious-g{generation}",
        task=task,
        assignment=assignment,
        parent_assignment=dict(parent),
        changed_holes=(real_hole, decoy_hole),
        claim_hole=decoy_hole,  # the lie
        origin="adversary",
        generation=generation,
        metadata={"intent": "spurious_claim"},
    )
