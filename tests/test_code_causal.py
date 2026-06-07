"""Causal-by-revert on executing code: the original gate, made concrete."""

from rsi_foundry.code import synthesis, tasks
from rsi_foundry.code.code_foundry import CodeFoundry
from rsi_foundry.code.synthesis import Strategy


def test_honest_improving_claim_is_accepted():
    task = tasks.get_task("count_positive")
    f = CodeFoundry(task, Strategy("s"))
    parent = dict(task.seed)
    # init 1 -> 0 genuinely improves the visible pass-rate at the seed.
    cand = [c for c in synthesis.single_hole_candidates(task, parent, "init", 0)
            if c.metadata["value"] == "0"][0]
    ok, gates, ev = f.gate(cand)
    assert ok and gates["causal"]
    assert ev.gain > 0 and ev.attributed_fraction >= 0.5


def test_spurious_decoy_claim_is_rejected_by_revert():
    task = tasks.get_task("clamp")
    f = CodeFoundry(task, Strategy("s"))
    parent = dict(task.seed)
    # Fixes a REAL hole but claims the inert decoy; reverting the decoy keeps the gain.
    sp = synthesis.spurious_candidate(
        task, parent, real_hole="cmp_hi", real_value=task.correct["cmp_hi"],
        decoy_hole="decoy", decoy_value="2",
    )
    ok, gates, ev = f.gate(sp)
    assert not ok and not gates["causal"]
    assert ev.gain > 0            # the benchmark really did go up...
    assert ev.attributed_fraction < 0.5   # ...but not because of the claimed hole


def test_loop_never_promotes_an_unattributed_edit():
    for name in ("clamp", "sign", "count_positive"):
        task = tasks.get_task(name)
        result = CodeFoundry(task, Strategy("s"), seed=0).solve()
        for step in result.history:
            assert step.attributed_fraction >= 0.5
