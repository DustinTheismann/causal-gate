# causal-gate

A toy demonstrating **mechanism-attribution rejection of reward hacks** in a
self-improvement loop. Standard library + `pytest` only — no ML dependencies.
The "model" and "benchmark" are simulated on purpose, so the *gate logic* is the
entire object of study.

> **Honest limitation, up front.** This is a **CLASS-5 (informed-inference)
> artifact**: it is *simulated, not empirical*. It shows that the gate logic is
> coherent and not overfit to one planted hack. It does **not** show that
> causal-claim defense is cheaper than formal verification on real models. That
> is the open question — and the thing that could kill the whole approach. See
> [`FALSIFICATION.md`](./FALSIFICATION.md).

## The concept

A self-improvement loop accepts candidate modifications to a model.

- A **benchmark-only gate** accepts any modification whose score goes up. This is
  *gameable*: a modification can score higher for the wrong reason — a shortcut
  that exploits the benchmark rather than the thing the benchmark is meant to
  measure.
- A **causal gate** accepts a modification only if its stated **causal claim** —
  *"this helps because of mechanism M"* — survives an adversarial check that
  tries to show the gain comes from something other than M.

Every modification must therefore carry a `CausalClaim` naming the feature /
mechanism it says drives its improvement. The causal gate adversarially tests
that claim instead of trusting it.

## How the causal gate works (`src/causal_gate/causal_check.py`)

The gate is a **general** mechanism-attribution test. It contains **no reference
to any specific planted hack** — the test suite asserts this. Given the
*claimed* mechanism, it applies two general properties:

1. **Attribution (ablation).** Permute the claimed feature and recompute the
   modification's gain. If the gain *survives* the ablation of the claimed
   mechanism, the gain came from somewhere else, so the claim is false — reject,
   regardless of the benchmark score. (Permutation-importance applied to a
   *stated cause*: if it's load-bearing, knocking it out should bring the
   structure down.)
2. **Invariance.** Re-measure the gain across a family of environments in which
   spurious correlations are re-randomized (different strength, often flipped
   sign), while the causal law stays fixed. A genuine causal mechanism keeps
   paying off; an exploit's gain collapses or reverses. This catches an exploit
   *even when the modification honestly names it*, and it generalizes to
   exploits the gate has never seen.

The world (`task.py`) is the ground truth and knows which feature is causal. The
gate never does — it only asks the world for environments and probes whatever
mechanism the modification claims.

## Run it

```bash
pip install -e .
pip install pytest        # or: pip install -e ".[test]"
pytest -v
```

You can also watch the two gates disagree on the planted hack:

```bash
python -m causal_gate.loop
```

## What each test proves

| Test | Scenario | Benchmark gate | Causal gate | What it proves |
|------|----------|----------------|-------------|----------------|
| `test_legit_improvement.py` | gain truly from the claimed mechanism | accept | **accept** | the gate does not reject *real* improvements; the claim is load-bearing and invariant |
| `test_reward_hack.py` | gain from a shortcut; claim names the *real* mechanism | **accept** | **reject** | the core result — benchmark is fooled; the causal gate sees the gain survive ablation of the claimed mechanism |
| `test_fabricated_claim.py` | gain from a shortcut; claim *lies* about the mechanism (names a feature the model never reads) | accept | **reject** | a fabricated claim is still caught: ablating an unused mechanism removes none of the gain |
| `test_gate_not_overfit.py` | a **second, unseen** shortcut, claimed *honestly* | accept | **reject** | the gate is not a lookup table — an honest claim passes the ablation check, but the **general invariance property** still catches the new exploit; the check source names no specific feature |
| `test_threshold_sensitivity.py` | sweep `threshold`/`margin`/`n_envs` and a **stealth** exploit | — | — | the verdicts are robust to the constants for the *loud* canonical adversaries, **but** a shortcut-contaminated stealth exploit is **falsely accepted at the default margin** — robustness is a property of the operating point, not a free lunch |

`test_gate_not_overfit.py` is the important one for the "is this overfit?" worry:
it introduces a shortcut the gate has never been told about, has the adversary
*honestly* claim it (so the ablation check alone would accept it), and shows the
gate still rejects it via the general invariance property — then asserts by
source inspection that `causal_check.py` references no specific feature name.

`test_threshold_sensitivity.py` is the adversarial counterweight. The other tests
each pin one operating point; "all tests pass" therefore certifies *the verdicts
at the default constants*, not that they are robust to them. The sweep maps the
safe region of `(threshold, margin)`, shows the defaults are interior for the
loud canonical adversaries — and then exhibits a **stealth exploit the shipped
default margin (0.02) wrongly accepts**, recovered only by raising the margin or
sampling more environments. Don't let the green checks launder "robust" into
"correct at one point." See [`FALSIFICATION.md`](./FALSIFICATION.md) for the
write-up.

## Layout

```
causal-gate/
  README.md
  FALSIFICATION.md
  pyproject.toml
  src/causal_gate/
    __init__.py
    task.py          # simulated benchmark: true causal signal + exploitable shortcuts
    modification.py  # Modification = code change + CausalClaim (mechanism it claims)
    gates.py         # BenchmarkGate (score up) and CausalGate (claimed mechanism carries the gain)
    causal_check.py  # the adversarial check: ablate/permute the claimed mechanism + invariance
    loop.py          # self-improvement loop routing modifications through a chosen gate
  tests/
    test_legit_improvement.py
    test_reward_hack.py
    test_fabricated_claim.py
    test_gate_not_overfit.py
```
