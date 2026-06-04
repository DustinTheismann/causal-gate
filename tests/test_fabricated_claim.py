"""An adversary that fabricates its causal claim.

Here the modification reads *only* the shortcut (zero weight on the causal
feature) yet claims its gain comes from true_signal -- a mechanism it does not
use at all. This is a more brazen lie than the reward hack. The causal gate must
still reject it: ablating a mechanism the model never reads cannot remove any
gain, so the gain is left fully in place and the claim is exposed as false.
"""

from causal_gate import CausalGate, CausalClaim, Model, Modification


def make_fabricated():
    model = Model({"shortcut": 3.0})  # note: no true_signal weight at all
    return Modification(
        name="fabricated_claim",
        model=model,
        claim=CausalClaim("true_signal", "fabricated: pretends to use the real signal"),
    )


def test_model_does_not_even_use_claimed_feature():
    mod = make_fabricated()
    assert not mod.model.reads("true_signal")


def test_causal_gate_rejects_via_ablation(task, baseline):
    decision = CausalGate(task).evaluate(baseline, make_fabricated())
    assert not decision.accepted
    assert decision.checks["benchmark_gain"]
    assert not decision.checks["attribution"]
    # Ablating the (unused) claimed feature changes nothing: gain survives whole.
    assert decision.metrics["gain_after_ablation"] > 0
    assert decision.metrics["attributed_fraction"] < 0.5
