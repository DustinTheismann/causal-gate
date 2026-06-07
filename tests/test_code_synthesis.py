"""The loop synthesizes real, correct programs by governed single-hole edits."""

import pytest

from rsi_foundry.code import execution, tasks
from rsi_foundry.code.code_foundry import CodeFoundry
from rsi_foundry.code.synthesis import Strategy

LEARNED = Strategy("lazy", lazy_causal=True, tie_break_bandit=True)


@pytest.mark.parametrize("task_name", ["clamp", "sign", "count_positive"])
def test_loop_solves_task_and_program_really_passes(task_name):
    task = tasks.get_task(task_name)
    result = CodeFoundry(task, LEARNED, seed=0).solve(budget=30)
    assert result.solved

    # The final source is valid Python and passes ALL real tests (visible + held).
    compile(result.source, task_name, "exec")
    res = execution.run(result.source, task.entry, task.visible + task.held)
    assert res.ok and res.pass_rate == 1.0


@pytest.mark.parametrize("task_name", ["clamp", "sign", "count_positive"])
def test_every_promoted_edit_is_single_mechanism(task_name):
    task = tasks.get_task(task_name)
    result = CodeFoundry(task, LEARNED, seed=0).solve(budget=30)
    # Each accepted step survived the causal gate: its claimed hole carried the gain.
    assert result.history
    for step in result.history:
        assert step.attributed_fraction >= 0.5


def test_solving_is_deterministic():
    task = tasks.get_task("count_positive")
    a = CodeFoundry(task, LEARNED, seed=0).solve()
    b = CodeFoundry(task, LEARNED, seed=0).solve()
    assert a.source == b.source and a.evals == b.evals
