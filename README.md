# Recursive R&D Foundry

A governed **recursive self-improvement scaffold**. AI systems generate successor
candidates, evaluate them, learn from failures, and promote only candidates that
clear a stack of gates: **novelty, causal, benchmark, containment, contracts, and
HALF-LIFE assurance**. Standard library + `pytest` only.

There are now **two layers**:

1. A **real** code-improvement substrate (`rsi_foundry/code/`) — actual program
   synthesis executed against actual unit tests in a sandboxed subprocess, with
   real learning from execution feedback and a meta-loop that improves its own
   improver. This is not simulated: it generates real Python, runs it, and the
   causal-by-revert gate reverts a real edit and re-runs real tests.
2. A **governance reference model** (`rsi_foundry/` core/loops/governance/...) —
   the seven-gate promotion rule over a *simulated* capability world, used to
   study the assurance logic (HALF-LIFE, contracts, MAP-Elites, POET) at a scale
   the real substrate has not yet reached.

> **Honest limitation, up front.** The real substrate is *real but small*: code
> generation is **sketch-based program synthesis** (search over a bounded space of
> hole-fillings), **not** an LLM, so it reaches small repair-style programs, not
> arbitrary code; "training" is a real bandit + policy-selection, **not** neural
> training; there is no Git/Docker/Lean integration. The governance layer is still
> **simulated** — the cited research (Darwin Gödel Machine, AlphaEvolve, ADAS,
> SEAL, AI Scientist, MAP-Elites, POET, LeanDojo, MLE/RE/SWE-bench) is the
> *motivation*, not reproduced results. What is demonstrated: the loop genuinely
> generates, executes, and improves real code under a causal/regression/containment
> gate, and the governance logic is coherent and composable. What is **not**:
> that any of this is cheap or sound at real-model scale. See
> [`FALSIFICATION.md`](./FALSIFICATION.md).

## The real layer: generate, execute, improve (`rsi_foundry/code/`)

```bash
python examples/run_code_improvement.py
```

Given a deliberately-wrong seed program, the loop proposes single-hole edits,
**executes each in a sandboxed subprocess** against real unit tests, and promotes
the best edit that passes every gate — containment (real isolation + safety scan +
timeout), benchmark (visible pass-rate up), regression (no previously-passing test
breaks), and **causal** (reverting the *claimed* edit destroys the gain, and the
gain holds on a held-out test split). Because the causal gate demands single-hole
attribution, the program is improved by a sequence of individually-justified edits
until it passes 100% of the real tests.

| What | Status now | Where |
|------|-----------|-------|
| Code generation | **real** (sketch/hole program synthesis, emits real Python) | `code/synthesis.py`, `code/tasks.py` |
| Benchmark | **real** (unit tests executed on generated code) | `code/execution.py` |
| Sandbox / containment | **real** (isolated subprocess, rlimit, timeout, static scan) | `code/execution.py` |
| Causal gate | **real** (revert the claimed edit + re-run; held-out generalization) | `code/evaluation.py` |
| Learning / "training" | **real** (UCB bandit + lazy-causal policy from execution feedback) | `training/operator_bandit.py`, `code/code_foundry.py` |
| Meta self-improvement | **real** (measure candidate policies, adopt the cheaper one if gated) | `code/meta.py` |
| HALF-LIFE / contracts / QD / POET | **simulated** (governance reference model) | `governance/`, `loops/`, `evals/` |

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
    code/        # REAL layer: tasks, execution (sandbox), synthesis, evaluation,
                 #            code_foundry (the loop), meta (self-improvement)
    core/        # types, policy, mini-yaml, context, registry, runpack, orchestrator
    loops/       # dgm, alphaevolve, adas, scientist, novelty+QD, best-attribute
    training/    # seal (failure-mined self-training), operator_bandit (real learning)
    governance/  # causal_gate, half_life, promotion
    verification/# proof-carrying contracts
    sandbox/     # containment
    connectors/  # benchmark adapters + evaluator quorum
    evals/       # harness, poet
  examples/      # run_minimal_cycle.py (governance), run_code_improvement.py (real)
  tests/         # governance suite + test_code_* (execute real generated code)
```

This repository is the runnable spine. Turning the simulated seams (benchmark,
sandbox, proof) into real ones — Git patches, Docker, SWE/MLE-Bench, Lean — is the
v0.3 work, and `docs/ARCHITECTURE.md` lists the seams in dependency order.
