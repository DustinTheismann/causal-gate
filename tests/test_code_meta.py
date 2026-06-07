"""Meta self-improvement: the loop edits and selects its own improver, gated."""

from rsi_foundry.code import meta, tasks
from rsi_foundry.code.synthesis import Strategy

INCUMBENT = Strategy("baseline", lazy_causal=False, tie_break_bandit=False)
CHEAPER = Strategy("lazy", lazy_causal=True, tie_break_bandit=False)
TRAIN = [tasks.get_task("clamp"), tasks.get_task("count_positive")]
VALIDATE = [tasks.get_task("sign")]


def test_adopts_a_strictly_cheaper_strategy_that_keeps_capability():
    res = meta.search(INCUMBENT, [CHEAPER], TRAIN, VALIDATE)
    assert res.adopted and res.chosen.name == "lazy"
    assert res.scores["lazy"].total_evals < res.scores["baseline"].total_evals
    assert res.scores["lazy"].solved_all
    assert res.validate_solved  # the improvement generalizes to a held-out task


def test_adoption_is_gated_no_cheaper_option_keeps_incumbent():
    # Only the incumbent in the candidate set -> nothing strictly cheaper -> keep it.
    res = meta.search(INCUMBENT, [], TRAIN, VALIDATE)
    assert not res.adopted and res.chosen.name == "baseline"


def test_meta_never_adopts_a_strategy_that_loses_capability():
    # A "fast but broken" strategy that fails to solve must never be adopted,
    # even if it would look cheaper. Budget 1 forces incompleteness.
    crippled = Strategy("crippled", lazy_causal=True, tie_break_bandit=True)
    res = meta.search(INCUMBENT, [crippled], TRAIN, VALIDATE, budget=1)
    # With budget 1 neither solves all; adoption must be refused or land on a solver.
    if res.adopted:
        assert res.scores[res.chosen.name].solved_all
