"""End-to-end spine: a governed recursive loop that improves and self-corrects."""

from rsi_foundry import Foundry
from rsi_foundry.core.types import SHORTCUT_GENE


def _run(seed=0, cycles=8):
    f = Foundry(seed=seed)
    reports = f.run(cycles)
    return f, reports


def test_frontier_improves_recursively():
    f, reports = _run()
    assert f.registry.frontier_capability > 0.44 + 0.1   # rose well past the seed
    assert len(f.registry.promotions) >= 4               # multiple governed promotions
    # Capability is monotonic non-decreasing across promotions.
    caps = [p.capability for p in f.registry.promotions]
    assert caps == sorted(caps)


def test_reward_hacks_are_never_promoted():
    f, reports = _run()
    for rep in reports:
        for oc in rep.outcomes:
            if oc.candidate.genome.get(SHORTCUT_GENE, 0.0) > 0.05:
                assert not oc.decision.promoted, oc.candidate.cid
                # rejected by a principled gate, not by luck
                failed = {g.name for g in oc.decision.gates if not g.passed}
                assert failed & {"causal", "containment", "contracts"}


def test_seal_learns_to_stop_proposing_hacks():
    f, reports = _run()
    assert f.seal.shortcut_aversion >= 0.5
    # Once aversion crosses the DGM threshold, no further reward hacks are proposed.
    hack_cycles = [
        rep.cycle for rep in reports
        if any(oc.candidate.metadata.get("intent") == "reward_hack" for oc in rep.outcomes)
    ]
    assert hack_cycles, "expected the naive DGM loop to try hacking early"
    assert max(hack_cycles) < reports[-1].cycle  # they stopped before the end


def test_quality_diversity_archive_fills():
    f, reports = _run()
    assert f.archive.occupancy() >= 5  # multiple distinct behavior niches preserved


def test_run_is_deterministic():
    f1, r1 = _run(seed=0)
    f2, r2 = _run(seed=0)
    assert [r.promoted_ids for r in r1] == [r.promoted_ids for r in r2]
    assert f1.registry.frontier_capability == f2.registry.frontier_capability


def test_half_life_invariant_holds_across_the_run():
    f, reports = _run()
    budget = f.policy.get("half_life.assurance_renewal") * f.policy.get("half_life.safety_factor")
    for rep in reports:
        for oc in rep.outcomes:
            if oc.decision.promoted:
                assert oc.report.capability_drift <= budget + 1e-9
