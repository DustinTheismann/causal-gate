"""A legitimate improvement: the gain truly comes from the claimed mechanism.

The modification leans harder on the causal feature and drops the distractor.
The claim ("gain from true_signal") is true, so BOTH gates accept it.
"""

from causal_gate import BenchmarkGate, CausalGate, CausalClaim, Model, Modification


def make_legit():
    return Modification(
        name="legit",
        # Trust the real signal, drop the distractor.
        model=Model({"true_signal": 1.0}),
        claim=CausalClaim("true_signal", "relies on the genuinely causal feature"),
    )


def test_benchmark_gate_accepts(task, baseline):
    decision = BenchmarkGate(task).evaluate(baseline, make_legit())
    assert decision.accepted
    assert decision.metrics["gain"] > 0


def test_causal_gate_accepts(task, baseline):
    decision = CausalGate(task).evaluate(baseline, make_legit())
    assert decision.accepted, decision.reason
    # The claimed mechanism is load-bearing...
    assert decision.checks["attribution"]
    # ...and the gain is invariant across re-randomized environments.
    assert decision.checks["invariance"]
    assert decision.metrics["min_env_gain"] > 0
