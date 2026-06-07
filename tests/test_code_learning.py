"""Real learning from execution feedback: cheaper search, learned operator value."""

from rsi_foundry.code import tasks
from rsi_foundry.code.code_foundry import CodeFoundry
from rsi_foundry.code.synthesis import Strategy

# Vary ONLY lazy_causal so the comparison isolates that optimization.
LAZY = Strategy("lazy_only", lazy_causal=True, tie_break_bandit=False)
BASELINE = Strategy("baseline", lazy_causal=False, tie_break_bandit=False)
ALL = ["clamp", "sign", "count_positive"]


def test_lazy_causal_is_sound_and_cheaper():
    learned_total = baseline_total = 0
    for name in ALL:
        task = tasks.get_task(name)
        learned = CodeFoundry(task, LAZY, seed=0).solve()
        baseline = CodeFoundry(task, BASELINE, seed=0).solve()
        # Same capability and the SAME solution (lazy verification changes no outcome)...
        assert learned.solved and baseline.solved
        assert learned.source == baseline.source
        # ...at no greater cost.
        assert learned.evals <= baseline.evals
        learned_total += learned.evals
        baseline_total += baseline.evals
    assert learned_total < baseline_total  # strictly cheaper overall


def test_bandit_learns_which_operators_pay_off():
    task = tasks.get_task("clamp")
    f = CodeFoundry(task, LAZY, seed=0)
    f.solve()
    # A hole that drove real gains outranks the provably-inert decoy.
    productive = max(
        (h for h in task.hole_names() if h != "decoy"),
        key=lambda h: f.bandit.value(h),
    )
    assert f.bandit.value(productive) > f.bandit.value("decoy")


def test_inert_decoy_is_observed_inert():
    task = tasks.get_task("clamp")
    result = CodeFoundry(task, LAZY, seed=0).solve()
    assert "decoy" in result.inert_holes
