"""Real program-synthesis tasks (sketches with holes).

This replaces the simulated "benchmark scoring function" with actual code that is
executed against actual unit tests. A task is a *sketch*: valid Python with a few
named holes, each ranging over a small set of concrete code fragments. Filling the
holes renders a real source string defining the entry function; the synthesizer's
job is to find a filling that passes the tests.

Each task ships a deliberately wrong ``seed`` filling (the starting point to be
improved) and the known ``correct`` filling (used only by tests as an oracle, never
by the search). Tests are split into ``visible`` (what the search optimizes and the
benchmark scores) and ``held`` (a generalization split the causal invariance check
uses, so a filling that overfits the visible cases is caught).

``clamp`` also carries a ``decoy`` hole that provably cannot affect the output -- the
code analog of a spurious feature, used to demonstrate the causal-by-revert gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# A test is (args, expected). args is JSON-serializable (call entry(*args)).
Test = Tuple[list, object]


@dataclass
class SketchTask:
    name: str
    entry: str
    sketch: str
    holes: Dict[str, List[str]]
    seed: Dict[str, str]
    correct: Dict[str, str]
    visible: List[Test]
    held: List[Test]
    decoy_holes: Tuple[str, ...] = ()  # holes that cannot affect behavior

    def render(self, assignment: Dict[str, str]) -> str:
        filled = dict(self.seed)
        filled.update(assignment)
        return self.sketch.format(**filled)

    def hole_names(self) -> List[str]:
        return list(self.holes)


_CLAMP = SketchTask(
    name="clamp",
    entry="solve",
    sketch=(
        "def solve(x, lo, hi):\n"
        "    note = {decoy}\n"            # decoy: never read again
        "    if x {cmp_lo} lo:\n"
        "        return {ret_lo}\n"
        "    if x {cmp_hi} hi:\n"
        "        return {ret_hi}\n"
        "    return x\n"
    ),
    holes={
        "cmp_lo": ["<", "<=", ">", ">="],
        "ret_lo": ["lo", "x", "hi"],
        "cmp_hi": ["<", "<=", ">", ">="],
        "ret_hi": ["hi", "x", "lo"],
        "decoy": ["0", "1", "2"],
    },
    # Fully-wrong but single-hole greedy-solvable (verified); decoy starts off-value.
    seed={"cmp_lo": "<=", "ret_lo": "hi", "cmp_hi": "<", "ret_hi": "hi", "decoy": "1"},
    correct={"cmp_lo": "<", "ret_lo": "lo", "cmp_hi": ">", "ret_hi": "hi", "decoy": "0"},
    visible=[([5, 0, 10], 5), ([-3, 0, 10], 0), ([20, 0, 10], 10), ([0, 0, 10], 0)],
    held=[([10, 0, 10], 10), ([7, 1, 5], 5), ([-1, -5, -2], -2), ([-9, -5, -2], -5)],
    decoy_holes=("decoy",),
)

_SIGN = SketchTask(
    name="sign",
    entry="solve",
    sketch=(
        "def solve(n):\n"
        "    if n {cmp_pos} 0:\n"
        "        return {pos}\n"
        "    if n {cmp_neg} 0:\n"
        "        return {neg}\n"
        "    return {zero}\n"
    ),
    holes={
        "cmp_pos": [">", "<", ">=", "<="],
        "pos": ["1", "-1", "0"],
        "cmp_neg": ["<", ">", "<=", ">="],
        "neg": ["-1", "1", "0"],
        "zero": ["0", "1", "-1"],
    },
    seed={"cmp_pos": "<", "pos": "0", "cmp_neg": ">", "neg": "0", "zero": "1"},
    correct={"cmp_pos": ">", "pos": "1", "cmp_neg": "<", "neg": "-1", "zero": "0"},
    visible=[([5], 1), ([-5], -1), ([0], 0)],
    held=[([100], 1), ([-1], -1), ([42], 1), ([-99], -1)],
)

_COUNT_POS = SketchTask(
    name="count_positive",
    entry="solve",
    sketch=(
        "def solve(xs):\n"
        "    c = {init}\n"
        "    for v in xs:\n"
        "        if v {cmp} 0:\n"
        "            c = c {op} 1\n"
        "    return c\n"
    ),
    holes={"init": ["0", "1"], "cmp": [">", "<", ">=", "<="], "op": ["+", "-"]},
    seed={"init": "1", "cmp": "<", "op": "-"},
    correct={"init": "0", "cmp": ">", "op": "+"},
    visible=[([[1, -2, 3, 0, 4]], 3), ([[]], 0), ([[-1, -2]], 0)],
    held=[([[5, 5, 5]], 3), ([[0, 0, 0]], 0), ([[-1, 2, -3, 4]], 2)],
)

_TASKS = {t.name: t for t in (_CLAMP, _SIGN, _COUNT_POS)}


def all_tasks() -> List[SketchTask]:
    return list(_TASKS.values())


def get_task(name: str) -> SketchTask:
    return _TASKS[name]
