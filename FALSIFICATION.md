# FALSIFICATION

## What this artifact is

**Class:** CLASS-5 — *informed inference*. This repository is a **simulation**,
not an empirical result. There is no real model, no real benchmark, and no real
self-improvement. The "model" is a linear-threshold function over named
features; the "benchmark" is accuracy on a synthetic dataset; the "mechanisms"
are individual features whose causal status is stipulated by the world
generator.

## What it does demonstrate

Within the simulation, it demonstrates that the **causal-acceptance-gate logic
is coherent and not overfit to a single planted hack**:

1. A legitimate improvement, whose gain genuinely comes from the claimed
   mechanism, is accepted by both gates.
2. A planted reward hack — gain from a shortcut, with a causal claim that names
   the *real* mechanism — is accepted by the benchmark gate and **rejected** by
   the causal gate, because the gain survives ablation of the claimed mechanism.
3. A fabricated claim (naming a mechanism the model never uses) is also rejected.
4. A **second, different shortcut the gate has never seen** — claimed *honestly*,
   so that the ablation check alone would accept it — is still rejected by the
   gate's general invariance property. The check module names no specific
   feature of the world (asserted by source inspection). The defense is a general
   property, not a lookup table keyed to the planted hack.

That is the whole and only claim: **the gate logic is internally coherent and
general across at least one shortcut it was never shown.**

## What it does NOT demonstrate (the open question)

It does **not** demonstrate that **causal-claim defense is cheaper than formal
proof on real models.** That is the entire bet of the "middle path" — that
adversarially checking a stated causal mechanism is materially less expensive
than exhaustive/formal verification, while being materially more robust than a
benchmark score. Nothing here speaks to that. The cost structure of real
mechanism attribution (interventions on real models, real distribution shift,
real adversaries who design claims to survive the check) is exactly what is
abstracted away.

## The specific result that would falsify the idea

The approach dies if **the ablation/invariance-based check cannot be made to
generalize beyond planted shortcuts without becoming as expensive as exhaustive
verification.**

Concretely, the idea is falsified if any of the following hold on real systems:

- **No cheap environment family.** The invariance check depends on a supply of
  environments in which spurious correlations are re-randomized while the causal
  law holds. If constructing such interventions for a real model is itself as
  costly as formal verification (or impossible without already knowing the true
  mechanism), the middle path collapses into the expensive path it was meant to
  avoid.
- **Adversarial claims that survive a bounded check.** If, for any fixed-budget
  attribution/invariance procedure, an adversary can reliably craft a
  modification whose gain rides on a hidden mechanism yet survives the check
  (e.g., a shortcut engineered to be invariant across the *particular*
  environments the gate can afford to sample), then passing the gate stops being
  evidence of a true mechanism.
- **Generalization requires exhaustion.** If catching the *n+1*-th novel shortcut
  reliably requires enumerating shortcuts (or environments, or interventions) in
  a way that scales with the size of the hypothesis space — i.e., the only way to
  make the check general is to make it exhaustive — then there is no middle path:
  it is just verification with extra steps.

In this toy, none of these bite *for the four canonical scenarios*, because the
world hands the gate a perfect environment family and those adversaries are loud.
On real models, any one of them landing kills the approach. This repository is
evidence that the *logic* is worth taking to that harder test — and nothing more.

## Empirical note: the constants do the discriminating, and they are not derived

`tests/test_threshold_sensitivity.py` sweeps the gate's two free constants
(`attribution_threshold = 0.5`, `invariance_margin = 0.02`) and the environment
sample size. Two findings are worth stating plainly, because the four canonical
tests hide them:

1. **The defaults look robust only because the canonical adversaries are loud.**
   Across five seeds there is a wide band of `(threshold, margin)` that classifies
   all four canonical scenarios correctly, and the defaults sit well inside it
   with slack far larger than the accuracy quantum. Taken alone, this invites the
   conclusion that the constants don't matter much. They do.

2. **A stealth adversary turns the margin into the whole decision — and the
   shipped default gets it wrong.** A shortcut-contaminated modification whose
   gain stays *net-positive across the sampled environments* (worst sampled-env
   gain ≈ +0.055) is **accepted at the default margin of 0.02**. It is rejected
   only by (a) raising the margin above its worst sampled-env gain or (b)
   sampling enough additional environments to reach the adverse tail. Correctness
   on this adversary is therefore set jointly by `invariance_margin` and
   `n_envs` — neither of which has a principled value here. This is killers #1 and
   #2 above, reproduced as an executing test rather than asserted in prose.

The honest reading: **"all tests pass" certifies the verdicts at one operating
point; it does not certify robustness, and a stealth exploit exists inside the
toy that the shipped defaults wave through.** Deriving `invariance_margin` from a
stated per-environment noise model (so it is a function of the world rather than
a number chosen by looking at the answer) is the obvious next step — and whether
that derivation stays cheap on real models is, again, the open question.
