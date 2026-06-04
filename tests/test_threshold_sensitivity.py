"""Threshold-sensitivity / robustness sweep -- the adversarial test of the gate.

The other four test files each pin ONE point in parameter space and check the
verdict is right there. "9 tests pass" therefore establishes *the verdicts are
correct at the default `(attribution_threshold, invariance_margin, seed,
n_envs)`* -- and nothing about whether they are *robust* to those constants. The
discriminating power of `CausalGate` lives in two hand-set numbers
(`threshold=0.5`, `margin=0.02`); this file is the instrument that asks where the
verdicts flip when you move them.

It does two things:

* PART A -- maps the safe region of `(threshold, margin)` over which all four
  canonical scenarios get the right verdict, across several world seeds, and
  shows the defaults sit comfortably inside it AND that the verdicts flip just
  outside it (so the sweep exercises real failure, not vacuous success).

* PART B -- the actual break. It builds a *stealth* exploit -- a shortcut-
  contaminated modification whose gain stays net-positive across the SAMPLED
  environments -- and shows the default gate ACCEPTS it. This is a documented
  false-accept: the canonical suite contains no such adversary, so its green
  checks are perfectly consistent with the gate failing here. The verdict is
  recovered only by raising the margin above the exploit's `min_env_gain` or by
  sampling more environments -- i.e., correctness on a stealth adversary is set
  by two free parameters, not by a principle. (See FALSIFICATION.md killers #1
  and #2.)

These are robustness / characterization tests. Some assertions deliberately pin
a *failure* so that any future change which moves the boundary trips the test and
forces a conscious decision.
"""

from __future__ import annotations

import inspect

import pytest

from causal_gate import (
    CausalClaim,
    CausalGate,
    Model,
    Modification,
    Task,
)

# Keep the defaults under test in lock-step with the gate's real signature, so
# this file can never silently drift from what CausalGate actually ships.
_PARAMS = inspect.signature(CausalGate.__init__).parameters
DEFAULT_THRESHOLD = _PARAMS["attribution_threshold"].default
DEFAULT_MARGIN = _PARAMS["invariance_margin"].default
DEFAULT_N_ENVS = _PARAMS["n_envs"].default

BASELINE = {"true_signal": 0.4, "noise": 1.0}
ACCURACY_QUANTUM = 1.0 / 600  # score is accuracy over Task.n == 600 examples


# --------------------------------------------------------------------------- #
# Canonical scenarios. Each returns (task, baseline, modification, want_accept).
# --------------------------------------------------------------------------- #
def _canonical(seed: int):
    task = Task(seed=seed)
    novel = Task(shortcut_features=["shortcut_v2"], seed=seed + 50)
    base = Model(dict(BASELINE))
    return [
        (
            "legit",
            task,
            base,
            Modification("legit", Model({"true_signal": 1.0}),
                         CausalClaim("true_signal")),
            True,
        ),
        (
            "reward_hack",
            task,
            base,
            Modification("reward_hack",
                         Model({"true_signal": 0.4, "noise": 1.0, "shortcut": 3.0}),
                         CausalClaim("true_signal")),
            False,
        ),
        (
            "fabricated",
            task,
            base,
            Modification("fabricated", Model({"shortcut": 3.0}),
                         CausalClaim("true_signal")),
            False,
        ),
        (
            "novel_honest",
            novel,
            base,
            Modification("novel_honest",
                         Model({"true_signal": 0.4, "noise": 1.0, "shortcut_v2": 3.0}),
                         CausalClaim("shortcut_v2")),
            False,
        ),
    ]


def _metrics(task, baseline, modification):
    """Pull the (gain, attributed_fraction, min_env_gain) for a scenario once.

    These three numbers are independent of `threshold`/`margin` (those only gate
    the accept flag), so the entire (threshold, margin) sweep can be evaluated
    analytically from them -- and faithfully, because it reuses exactly the
    gate's own decision logic below.
    """
    decision = CausalGate(task).evaluate(baseline, modification)
    return (
        decision.metrics["gain"],
        decision.metrics["attributed_fraction"],
        decision.metrics["min_env_gain"],
    )


def _accepts(metrics, threshold: float, margin: float) -> bool:
    """Reproduce CausalGate's accept rule exactly (verified against gates.py)."""
    gain, frac, min_env_gain = metrics
    benchmark_ok = gain > 0.0
    attribution_ok = benchmark_ok and frac >= threshold
    invariance_ok = min_env_gain >= margin
    return benchmark_ok and attribution_ok and invariance_ok


def _accepts_rule_matches_gate():
    """Sanity: the analytic rule agrees with a live gate at a few points."""
    task, base = Task(seed=0), Model(dict(BASELINE))
    mod = Modification("rh",
                       Model({"true_signal": 0.4, "noise": 1.0, "shortcut": 3.0}),
                       CausalClaim("true_signal"))
    m = _metrics(task, base, mod)
    for t in (0.0, 0.5, 1.0):
        for mg in (-0.5, 0.02, 0.4):
            live = CausalGate(task, attribution_threshold=t,
                              invariance_margin=mg).evaluate(base, mod).accepted
            assert _accepts(m, t, mg) == live


# --------------------------------------------------------------------------- #
# PART A -- the safe region of (threshold, margin)
# --------------------------------------------------------------------------- #
SEEDS = (0, 1, 2, 3, 7)
THRESH_GRID = [round(-0.5 + 0.05 * i, 3) for i in range(41)]   # -0.50 .. 1.50
MARGIN_GRID = [round(-0.80 + 0.02 * i, 3) for i in range(71)]  # -0.80 .. 0.60


def _safe_set(seed):
    """All (threshold, margin) on the grid where every canonical verdict is right."""
    scen_metrics = [(want, _metrics(t, b, m)) for _, t, b, m, want in _canonical(seed)]
    safe = set()
    for thr in THRESH_GRID:
        for mar in MARGIN_GRID:
            if all(_accepts(met, thr, mar) == want for want, met in scen_metrics):
                safe.add((thr, mar))
    return safe


def test_accepts_rule_is_faithful_to_the_gate():
    _accepts_rule_matches_gate()


def test_defaults_are_inside_the_canonical_safe_region_for_every_seed():
    for seed in SEEDS:
        safe = _safe_set(seed)
        assert safe, f"no (threshold, margin) gets all four right at seed {seed}"
        assert (DEFAULT_THRESHOLD, DEFAULT_MARGIN) in safe, (
            f"defaults ({DEFAULT_THRESHOLD}, {DEFAULT_MARGIN}) are outside the "
            f"canonical safe region at seed {seed}"
        )


def test_defaults_have_real_slack_not_a_knife_edge():
    """The canonical defaults are interior with slack far larger than the metric's
    quantization -- so the 'lumpy accuracy estimator' cannot flip these verdicts.
    """
    safe = _safe_set(0)
    margins_at_default_thr = sorted(m for (t, m) in safe if t == DEFAULT_THRESHOLD)
    thr_at_default_margin = sorted(t for (t, m) in safe if m == DEFAULT_MARGIN)

    margin_up = max(margins_at_default_thr) - DEFAULT_MARGIN
    margin_down = DEFAULT_MARGIN - min(margins_at_default_thr)
    thr_up = max(thr_at_default_margin) - DEFAULT_THRESHOLD
    thr_down = DEFAULT_THRESHOLD - min(thr_at_default_margin)

    # Generous slack on every side, all >> one-example wiggle (1/600 ~ 0.0017).
    for slack in (margin_up, margin_down, thr_up, thr_down):
        assert slack > 50 * ACCURACY_QUANTUM, (slack, ACCURACY_QUANTUM)


def test_verdicts_actually_flip_outside_the_band():
    """The sweep must exercise failure, or 'inside the band' means nothing."""
    scen = {name: _metrics(t, b, m) for name, t, b, m, _ in _canonical(0)}

    # Push the margin above legit's invariance headroom -> legit FALSE-rejects.
    assert _accepts(scen["legit"], DEFAULT_THRESHOLD, DEFAULT_MARGIN)
    assert not _accepts(scen["legit"], DEFAULT_THRESHOLD, 0.45)

    # Push the threshold above legit's attribution fraction -> legit FALSE-rejects.
    assert not _accepts(scen["legit"], 1.20, DEFAULT_MARGIN)

    # Drop margin below the novel shortcut's min env gain -> novel FALSE-accepts
    # (its honest claim already passes attribution, so only invariance guards it).
    assert not _accepts(scen["novel_honest"], DEFAULT_THRESHOLD, DEFAULT_MARGIN)
    assert _accepts(scen["novel_honest"], DEFAULT_THRESHOLD, -0.80)


# --------------------------------------------------------------------------- #
# PART B -- the stealth exploit: where the default gate actually breaks
# --------------------------------------------------------------------------- #
def _stealth():
    """Heavy shortcut contamination, but net-positive across the SAMPLED envs.

    Honestly claims the shortcut, so the ablation check is satisfied -- only the
    invariance margin stands between it and acceptance.
    """
    base = Model(dict(BASELINE))
    mod = Modification(
        "stealth",
        Model({"true_signal": 0.9, "noise": 1.0, "shortcut": 1.0}),
        CausalClaim("shortcut", "rides the shortcut but stays net-positive in sample"),
    )
    return Task(seed=0), base, mod


def test_stealth_exploit_is_a_known_false_accept_at_defaults():
    """DOCUMENTED LIMITATION: at the shipped defaults the gate ACCEPTS a shortcut-
    contaminated exploit, because its worst sampled-environment gain happens to
    clear the 0.02 margin. The canonical suite contains no such adversary, which
    is exactly why its green checks do not certify robustness.
    """
    task, base, mod = _stealth()
    decision = CausalGate(task).evaluate(base, mod)  # shipped defaults
    assert decision.accepted, "stealth behaviour changed -- re-derive the boundary"
    assert decision.checks["attribution"]  # honest claim passes ablation...
    assert decision.checks["invariance"]   # ...and squeaks past the margin
    assert decision.metrics["min_env_gain"] > DEFAULT_MARGIN


def test_margin_needed_to_reject_stealth_is_above_the_default():
    """The fix exists but is NOT the shipped value: the smallest margin that
    rejects the stealth exploit sits above 0.02 (yet below legit's headroom, so a
    better-tuned constant would catch it without breaking legit). The cutoff is a
    chosen number, not a derived one.
    """
    task, base, mod = _stealth()
    margins = [round(0.01 * i, 3) for i in range(0, 41)]  # 0.00 .. 0.40
    rejecting = [
        mg for mg in margins
        if not CausalGate(task, invariance_margin=mg).evaluate(base, mod).accepted
    ]
    smallest_rejecting = min(rejecting)
    assert smallest_rejecting > DEFAULT_MARGIN, smallest_rejecting
    # legit must survive that same margin, or the "fix" would break a true gain.
    legit_task = Task(seed=0)
    legit = Modification("legit", Model({"true_signal": 1.0}),
                         CausalClaim("true_signal"))
    assert CausalGate(legit_task,
                      invariance_margin=smallest_rejecting).evaluate(
                          Model(dict(BASELINE)), legit).accepted


@pytest.mark.parametrize("n_envs", [20, 30, 60])
def test_sampling_more_environments_also_catches_stealth(n_envs):
    """The other free parameter: with a richer environment family the adverse
    tail gets sampled, min_env_gain goes negative, and the same exploit is
    rejected at the SAME margin. Correctness here depends on how much of the tail
    you can afford to sample -- FALSIFICATION.md killer #1 in miniature.
    """
    task, base, mod = _stealth()
    assert CausalGate(task, n_envs=DEFAULT_N_ENVS).evaluate(base, mod).accepted
    assert not CausalGate(task, n_envs=n_envs).evaluate(base, mod).accepted
