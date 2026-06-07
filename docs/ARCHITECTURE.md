# Architecture

## Two layers

The repository has a **real** code-improvement substrate (`rsi_foundry/code/`) and a
**simulated** governance reference model (the rest of `rsi_foundry/`). They share the
same idea — improve only what survives a causal/regression/containment gate — but the
real layer runs actual generated Python against actual tests, while the governance
layer studies the assurance machinery (HALF-LIFE, contracts, QD, POET) on a simulated
capability world. The sections below cover the governance cycle; the real layer is
documented inline in `rsi_foundry/code/` and exercised by `tests/test_code_*.py`.

### The real layer in one paragraph

`code/tasks.py` defines sketch tasks (valid Python with holes). `code/synthesis.py`
renders real candidate source by filling a hole. `code/execution.py` runs that source
in an isolated subprocess (rlimit + timeout + static safety scan) against real unit
tests. `code/evaluation.py` computes the causal-by-revert evidence: revert the claimed
hole, re-run the real tests, and require the gain to vanish *and* to hold on a
held-out split. `code/code_foundry.py` is the best-improvement loop under those gates;
`training/operator_bandit.py` learns per-hole productivity; `code/meta.py` measures
candidate improver policies and adopts the cheaper one only if it loses no capability.

## One cycle, end to end

`Foundry.run_cycle()` (`rsi_foundry/core/orchestrator.py`) executes:

1. **Renew assurance.** `HalfLifeController.renew()` closes part of the gap between
   the promoted frontier and the assured level — assurance "does its work" before
   any new capability lands.
2. **Propose.** Four proposers each emit successor candidates against the current
   frontier, the MAP-Elites elite genomes, the recombined best-known genome, and
   the SEAL guidance:
   - `dgm_loop` — self-edit one gene (and, while still naive, a reward hack);
   - `alphaevolve_loop` — recombine two elites + mutation;
   - `adas_loop` — reallocate agent topology between skills;
   - `scientist_loop` — hypothesis-driven, ships proof-carrying contracts.
3. **Sandbox.** `sandbox/containment.py` measures each candidate's side-effect
   scope before it is allowed near the gates.
4. **Evaluate.** `evals/harness.py` gathers benchmark score, evaluator quorum,
   regression count, novelty, behavior descriptor, causal ablation evidence, and a
   risk estimate into one `EvalReport`. Measurement is kept strictly separate from
   judgement.
5. **Gate.** `governance/promotion.py` runs all seven gates. A candidate is
   *qualified* only if every gate passes.
6. **Promote one.** The best qualified candidate becomes the new frontier
   (`core/successor_registry.py`); `HalfLifeController.on_promote` widens the gap.
7. **Mine everything.** Win or lose, every candidate updates the Best-Attribute
   Registry (`loops/best_attribute_registry.py`) and the MAP-Elites archive
   (`loops/novelty_ledger.py`); every rejection updates SEAL
   (`training/seal_loop.py`).
8. **Coevolve.** `evals/poet.py` may spawn a harder environment once the frontier
   masters the suite.
9. **Record.** `core/runpack_exporter.py` freezes a reproducible RunPack.

## Why each layer earns its place

- **Causal gate** (`governance/causal_gate.py`) — the descendant of the original
  causal-gate artifact. It tests a stated mechanism with ablation (is the claimed
  gene load-bearing?) and invariance (does the gain survive environments that break
  spurious correlations?). It names no specific gene; `test_causal_gate.py` asserts
  this by source inspection and by catching an honestly-claimed shortcut via
  invariance alone.
- **HALF-LIFE** (`governance/half_life.py`) — the assurance control plane. The
  inequality `drift <= renewal × safety_factor` plus the GREEN→BLACK state machine
  is what makes "bounded capability growth" operational rather than aspirational.
- **Contracts** (`verification/contracts.py`) — proof-carrying patches. A high-risk
  mutation must ship discharged obligations that are *re-checked here*; a
  claimed-but-false contract fails verification, exactly like a false causal claim.
- **Containment** (`sandbox/containment.py`) — nothing is benchmarked or promoted
  live; scope is measured first.
- **Novelty + MAP-Elites** (`loops/novelty_ledger.py`) — anti-collapse. The archive
  keeps the best candidate *per behavior niche*, not just the global best.
- **Best-Attribute Registry** + **SEAL** — the "don't discard losers" engine.
  Traits are harvested from any candidate that did no harm; failures raise a
  shortcut-aversion the proposers obey, so reward-hacking stops without being
  hand-coded against.
- **POET** — keeps the benchmark non-stationary so successors cannot overfit it.

## Determinism

Everything is seeded through a single `random.Random` threaded via
`core/context.py`. Two `Foundry(seed=s)` instances produce identical histories;
`test_cycle.py` asserts this. The mini-YAML reader/writer (`core/_miniyaml.py`)
keeps policy and RunPack I/O dependency-free.

## The simulated seams, in dependency order (v0.3 work)

1. Real Git patch generation (replace genome edits with diffs).
2. Docker sandbox execution (replace the scope proxy).
3. SWE-bench Lite / local-repo benchmark adapter.
4. MLE-Bench adapter.
5. Evaluator quorum backed by a real model judge + real unit tests + static analysis.
6. QD archive over real behavior descriptors.
7. POET task generator over real environments.
8. Lean/proof-contract gate via LeanDojo.
9. RunPack replay CLI.
10. Lineage / gate / failure dashboard.

Each is a seam already present in the scaffold; the governance logic above does not
change when a seam is made real — which is exactly the property the simulation is
meant to establish before paying the cost of real integration.
