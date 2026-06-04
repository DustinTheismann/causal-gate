"""The gate must not have the planted hack hardcoded.

We build a *different* world with a brand-new shortcut, ``shortcut_v2``, that the
gate has never seen, and a modification that exploits it and -- crucially --
claims it *honestly* ("gain from shortcut_v2"). An honest, load-bearing claim
sails through the ablation check: knocking out shortcut_v2 does destroy the gain,
so attribution "holds". A gate that only knew how to ablate the claimed feature
would therefore ACCEPT a shortcut.

The general invariance property is what saves it: shortcut_v2's gain collapses
once its spurious correlation is re-randomized across environments, so the causal
gate rejects it anyway -- without any reference to the specific shortcut.

We also assert, by inspecting the source, that the check module never names a
specific shortcut. The defense is a general property, not a lookup table.
"""

import pathlib

from causal_gate import CausalGate, CausalClaim, Model, Modification, Task


def make_unseen_shortcut_world():
    # A different world whose shortcut is named something the gate never sees.
    task = Task(shortcut_features=["shortcut_v2"], seed=3)
    baseline = Model({"true_signal": 0.4, "noise": 1.0})
    mod = Modification(
        name="new_shortcut",
        model=Model({"true_signal": 0.4, "noise": 1.0, "shortcut_v2": 3.0}),
        # An HONEST claim: it really does ride on shortcut_v2.
        claim=CausalClaim("shortcut_v2", "honestly admits it uses this feature"),
    )
    return task, baseline, mod


def test_new_shortcut_is_still_caught():
    task, baseline, mod = make_unseen_shortcut_world()
    decision = CausalGate(task).evaluate(baseline, mod)

    assert not decision.accepted, decision.reason
    # The benchmark score really did go up...
    assert decision.checks["benchmark_gain"]
    # ...and because the claim is honest, the ablation check is satisfied:
    # a gate that only ablated the claimed feature would have accepted a shortcut.
    assert decision.checks["attribution"]
    # The general invariance property is what catches it.
    assert not decision.checks["invariance"]
    assert decision.metrics["min_env_gain"] < 0


def test_check_module_has_no_hardcoded_shortcut():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "causal_gate"
    check_text = (src / "causal_check.py").read_text()
    code_lines = [
        line for line in check_text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    code = "\n".join(code_lines)
    # The mechanism-attribution logic must not mention any specific shortcut
    # or the privileged causal feature by name.
    for forbidden in ("shortcut", "true_signal"):
        assert forbidden not in code, (
            f"causal_check.py references '{forbidden}' -- the gate must be general"
        )
