# Recursive R&D Foundry

A governed **recursive self-improvement scaffold**. AI systems generate successor
candidates, evaluate them, learn from failures, and promote only candidates that
clear a stack of gates: **novelty, causal, benchmark, containment, contracts, and
HALF-LIFE assurance**. Standard library + `pytest` only.

> **Honest limitation, up front.** Every "model", "benchmark", "sandbox", and
> "proof" here is **simulated**. The cited research directions (Darwin Gödel
> Machine, AlphaEvolve, ADAS, SEAL, AI Scientist, MAP-Elites, POET, LeanDojo,
> MLE/RE/SWE-bench) are the *motivation* for the architecture, **not** integrated
> systems and **not** reproduced results. What this repo demonstrates is that the
> **governance logic is coherent, composable, and not overfit** — successors only
> advance when a causally-evidenced, contained, assurance-bounded improvement
> survives every gate. It does **not** show that this governance is cheap or sound
> on real models. That is the open question. See
> [`FALSIFICATION.md`](./FALSIFICATION.md).

## The core conclusion

The viable path is not "one AI mutates itself freely." It is a recursive AI **R&D
factory**:

```
generate successors -> sandbox -> benchmark -> prove / test / ablate
  -> extract useful traits -> train future proposers on failures
  -> promote only governed improvements -> coevolve the benchmark -> repeat
```

The novel move is **recursive improvement without single-winner fixation**: losers
are not discarded. Their traits feed a Best-Attribute Registry, their niches fill a
MAP-Elites archive, and their failures become SEAL training signal. The generator,
the agent design, the training data, the benchmark, and the governance layer all
improve at once.

## The promotion rule

A successor advances only when **every** gate passes:

| Gate | Passes when |
|------|-------------|
| benchmark | `capability_drift > fitness_delta_threshold` |
| novelty | `novelty_score >= threshold` (anti-collapse) |
| regression | `regression_failures == 0` on protected tasks |
| containment | `side_effect_scope <= ceiling` (sandbox) |
| **causal** | claimed mechanism survives ablation **and** is invariant across environments |
| contracts | required proof-carrying obligations are discharged and re-checked |
| **HALF-LIFE** | `capability_drift <= assurance_renewal × safety_factor`, and state not RED/BLACK |

No single gate can promote a candidate; any gate can veto one. That defense in
depth is the deliberate answer to the known blind spot of any single check.

## HALF-LIFE: capability must not outrun assurance

The governing inequality is `capability_drift <= assurance_renewal × safety_factor`.
The control plane tracks the gap between the promoted frontier and the level
assurance has caught up to, and exposes operational states:

`GREEN` (promote) → `AMBER` (promote, watched) → `RED` (constrain) → `BLACK`
(freeze / degrade / shutdown).

A single over-large jump is refused outright, even from GREEN, because no amount of
accumulated assurance justifies a step the layer cannot test in one renewal period.

## Run it

```bash
pip install -e .
pip install pytest          # or: pip install -e ".[test]"
pytest -v
python examples/run_minimal_cycle.py
```

The example prints, per cycle, the frontier, HALF-LIFE state, the promoted
successor, filled MAP-Elites niches, POET spawns, and the SEAL shortcut-aversion
the foundry has *learned* from rejecting reward hacks — and writes a reproducible
RunPack.

## The research → mechanism map

| Layer | Research basis | Role here (`rsi_foundry/...`) |
|-------|----------------|-------------------------------|
| DGM loop | Darwin Gödel Machine / self-editing coding agents | `loops/dgm_loop.py` — self-edit as a patch, not a live mutation |
| AlphaEvolve loop | Evolutionary coding agent + evaluators | `loops/alphaevolve_loop.py` — recombine elites, select by fitness |
| ADAS loop | Automated Design of Agentic Systems | `loops/adas_loop.py` — search agent topology |
| SEAL loop | Self-Adapting LMs | `training/seal_loop.py` — failures become training signal |
| AI Scientist loop | Automated scientific workflow | `loops/scientist_loop.py` — hypothesis → proof-carrying patch |
| Benchmark layer | MLE/RE/SWE/ABC-Bench | `connectors/benchmark_adapters.py` — scored suite + evaluator quorum |
| Formal / contracts | LeanDojo / proof-carrying gates | `verification/contracts.py` — re-checked obligations |
| Quality-diversity | MAP-Elites | `loops/novelty_ledger.py` — best-per-niche archive |
| Environment coevolution | POET | `evals/poet.py` — benchmark hardens with the frontier |
| Trait inheritance | Recursive Capability Fusion | `loops/best_attribute_registry.py` |
| HALF-LIFE | assurance control plane | `governance/half_life.py` |
| RunPacks | reproducible experiment records | `core/runpack_exporter.py` |

## Layout

```
recursive_rnd_foundry/
  README.md  FALSIFICATION.md  pyproject.toml
  configs/policy.yaml          # every threshold a gate consults
  docs/ARCHITECTURE.md
  examples/run_minimal_cycle.py
  runpacks/minimal_cycle.runpack.yaml
  rsi_foundry/
    core/        # types, policy, mini-yaml, context, registry, runpack, orchestrator
    loops/       # dgm, alphaevolve, adas, scientist, novelty+QD, best-attribute
    training/    # seal (failure-mined self-training)
    governance/  # causal_gate, half_life, promotion
    verification/# proof-carrying contracts
    sandbox/     # containment
    connectors/  # benchmark adapters + evaluator quorum
    evals/       # harness, poet
  tests/         # spine, half-life, causal, novelty/QD, contracts, seal, poet, runpack
```

This repository is the runnable spine. Turning the simulated seams (benchmark,
sandbox, proof) into real ones — Git patches, Docker, SWE/MLE-Bench, Lean — is the
v0.3 work, and `docs/ARCHITECTURE.md` lists the seams in dependency order.
