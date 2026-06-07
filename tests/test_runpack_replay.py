"""RunPack export + replay: a recorded cycle reproduces deterministically."""

from rsi_foundry import Foundry
from rsi_foundry.core import runpack_exporter


def test_export_then_replay_round_trips(tmp_path):
    f = Foundry(seed=0, runpack_dir=tmp_path)
    rep = f.run_cycle()
    path = tmp_path / "cycle_0.runpack.yaml"
    assert path.exists()

    summary = runpack_exporter.replay(path)
    assert summary["cycle"] == 0
    assert summary["seed"] == 0
    assert summary["promoted_ids"] == rep.promoted_ids
    assert summary["n_candidates"] == len(rep.outcomes)


def test_runpack_is_deterministic_across_seeded_runs():
    a = Foundry(seed=0)
    b = Foundry(seed=0)
    pack_a = runpack_exporter.build(a.run_cycle(), a.policy.data, a.seed)
    pack_b = runpack_exporter.build(b.run_cycle(), b.policy.data, b.seed)
    assert pack_a == pack_b


def test_runpack_records_every_gate_verdict():
    f = Foundry(seed=1)
    pack = runpack_exporter.build(f.run_cycle(), f.policy.data, f.seed)
    gate_names = {g["name"] for c in pack["candidates"] for g in c["gates"]}
    assert {"benchmark", "novelty", "regression", "containment",
            "causal", "contracts", "half_life"} <= gate_names
