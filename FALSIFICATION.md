# FALSIFICATION

## What this artifact is

**Class:** CLASS-5 — *informed inference*. The Recursive R&D Foundry is a
**simulation**, not an empirical system. There is no real model, no real code
patch, no real sandbox, no real proof, and no real benchmark. An "agent" is a
genome of capability genes; a "benchmark" is a weighted scoring function; a
"sandbox run" is a divergence measurement; a "proof" is a re-checked predicate. The
research it cites (DGM, AlphaEvolve, ADAS, SEAL, AI Scientist, MAP-Elites, POET,
LeanDojo, MLE/RE/SWE/ABC-Bench) is **motivation for the architecture**, not work
reproduced here.

## What it does demonstrate

Within the simulation, the governance logic is **coherent, composable, and not
overfit**:

1. A governed recursive loop runs end to end and improves the frontier *only*
   through successors that pass every gate — then plateaus when governed
   improvements run out. It is not unbounded self-improvement.
2. A planted reward hack (gain from the spurious gene, honest-sounding causal
   claim) is rejected by the causal gate; the causal check names no specific gene
   (asserted by source inspection) and catches an honestly-claimed shortcut via the
   general invariance property.
3. HALF-LIFE refuses any single capability jump larger than one renewal period can
   absorb, and escalates GREEN→AMBER→RED→BLACK as the assurance gap grows,
   constraining promotion in RED/BLACK.
4. Proof-carrying contracts are *re-checked*: a high-risk candidate without a
   discharged safety obligation is rejected, and a candidate that *claims* a
   contract it does not satisfy fails verification.
5. The "don't discard losers" engine works: traits are harvested from rejected
   candidates, niches fill a MAP-Elites archive, and failures raise a
   shortcut-aversion the proposers obey — so reward-hacking stops emerging without
   any rule hand-coded against the specific hack.
6. POET keeps the benchmark non-stationary; RunPacks reproduce a cycle exactly.

That is the entire claim: **the governance is internally coherent and general
across the mechanisms it was built to handle, and the layers compose into one
defensible promotion rule.**

## What it does NOT demonstrate (the open questions)

- That any of these gates is **sound or cheap on real models**. Real ablation,
  real distribution shift, real adversaries, real proof obligations, and real
  containment are exactly what is abstracted away.
- That the **HALF-LIFE inequality is measurable in practice** — `assurance_renewal`
  is a chosen constant here; on real systems "how much capability can assurance
  absorb per period" has no obvious estimator.
- That defense-in-depth **closes** the causal gate's inherited blind spot rather
  than merely overlapping with it. The stealth-exploit weakness documented in the
  original causal-gate lineage still exists; here it is *contained* by other gates
  in this toy, not *solved*.

## The specific results that would falsify the idea

1. **No cheap mechanism attribution.** If, on real models, deciding whether a
   claimed mechanism is load-bearing-and-invariant costs as much as exhaustive
   verification, the causal gate is not a middle path — it is verification with
   extra steps.
2. **No principled assurance-renewal rate.** If `assurance_renewal` cannot be
   estimated from a stated assurance process, HALF-LIFE degenerates into a knob
   tuned to whatever growth rate the operator wanted, and "capability must not
   outrun assurance" becomes unfalsifiable.
3. **Gate overlap is not gate coverage.** If, across realistic adversaries, the
   seven gates fail *together* (an exploit that is simultaneously benchmark-up,
   contained, invariant-on-sampled-environments, contract-claiming, and
   slow-drifting), then "defense in depth" was an illusion of independence, and the
   composite rule is no stronger than its weakest member.
4. **Coevolution outruns assurance.** If POET-style environment generation expands
   the capability surface faster than assurance can renew over it, the very
   mechanism meant to prevent overfitting becomes an uncontrolled capability driver.

In this toy none of these bite, because the world is generous and the adversaries
are the ones the architecture was designed to catch. On real systems any one of
them landing kills the approach. This repository is evidence that the *governance
logic* is worth taking to that harder test — and nothing more.
