"""The Foundry orchestrator: one governed recursive R&D cycle, end to end.

    propose successors (DGM / AlphaEvolve / ADAS / Scientist)
      -> sandbox each (containment)
      -> evaluate each (benchmark, quorum, regression, novelty, causal ablation)
      -> gate each (benchmark, novelty, regression, containment, causal,
                    contracts, HALF-LIFE)
      -> promote the single best gate-passer to the frontier
      -> mine EVERY candidate: traits (best-attribute registry),
                               niches (MAP-Elites archive),
                               failures (SEAL self-training)
      -> coevolve the environment (POET)
      -> export a RunPack

The novel move is that losers are not discarded: their traits, niches, and failure
lessons feed the next generation, so the generator, the archive, the training
signal, and the benchmark all improve together -- recursive improvement without
single-winner fixation.
"""

from __future__ import annotations

import pathlib
import random
from typing import List, Optional

from ..connectors.benchmark_adapters import BenchmarkSuite, baseline_genome
from ..evals import harness, poet
from ..governance import promotion
from ..governance.half_life import HalfLifeController
from ..loops import adas_loop, alphaevolve_loop, dgm_loop, scientist_loop
from ..loops.best_attribute_registry import BestAttributeRegistry
from ..loops.novelty_ledger import Elite, NoveltyLedger
from ..sandbox import containment
from ..training.seal_loop import SealLoop
from . import runpack_exporter
from .context import ProposalContext
from .policy import Policy
from .successor_registry import SuccessorRegistry
from .types import SKILLS, CandidateOutcome, CycleReport

_PROPOSERS = (dgm_loop, alphaevolve_loop, adas_loop, scientist_loop)


class Foundry:
    def __init__(
        self,
        policy: Optional[Policy] = None,
        seed: int = 0,
        suite: Optional[BenchmarkSuite] = None,
        runpack_dir: "pathlib.Path | str | None" = None,
    ) -> None:
        self.policy = policy or Policy.load()
        self.rng = random.Random(seed)
        self.seed = seed
        self.suite = suite or BenchmarkSuite()

        frontier = baseline_genome()
        cap = self.suite.capability(frontier)
        self.registry = SuccessorRegistry(frontier_genome=frontier, frontier_capability=cap)
        self.archive = NoveltyLedger()
        self.best_attrs = BestAttributeRegistry()
        self.seal = SealLoop()
        self.halflife = HalfLifeController.from_policy(self.policy, cap)
        self.generation = 0
        self.runpack_dir = pathlib.Path(runpack_dir) if runpack_dir else None

        self._seed_archive(frontier, cap)

    def _seed_archive(self, frontier, cap) -> None:
        descriptor = harness.behavior_descriptor(frontier, cap)
        self.archive._genomes.append(dict(frontier))
        self.archive.elites[descriptor] = Elite(
            cid="frontier-0", genome=dict(frontier), descriptor=descriptor,
            capability=cap, parent_ids=(), origin="seed",
        )

    # -- one cycle ---------------------------------------------------------- #
    def run_cycle(self) -> CycleReport:
        gen = self.generation
        self.halflife.renew()  # assurance does its work before new capability lands

        frontier = dict(self.registry.frontier_genome)
        guidance = self.seal.guidance({g: self.best_attrs.get(g) for g in SKILLS})
        ctx = ProposalContext(
            frontier=frontier,
            generation=gen,
            rng=self.rng,
            guidance=guidance,
            elite_genomes=self.archive.elite_genomes(),
            best_genome=self.best_attrs.best_genome(frontier),
        )

        proposals = []
        for loop in _PROPOSERS:
            proposals.extend(loop.propose(ctx))

        ceiling = self.policy.get("promotion.max_side_effect_scope", 0.34)
        outcomes: List[CandidateOutcome] = []
        for cand in proposals:
            sandbox = containment.run(cand.genome, frontier, ceiling)
            report = harness.evaluate(
                cand, self.suite, frontier, self.archive, self.policy,
                sandbox.side_effect_scope,
            )
            decision = promotion.decide(
                cand, report, sandbox, self.suite, frontier, self.halflife, self.policy
            )
            # Mine EVERY candidate, winner or loser.
            self.best_attrs.update(cand, report)
            self.archive.consider(cand, report)
            if not decision.promoted:
                self.seal.record_failure(cand, decision)
                self.seal.add_preference(frontier, cand.genome, decision.reason)
            outcomes.append(CandidateOutcome(cand, report, decision))

        # Single frontier advance per cycle: the best gate-passer wins.
        qualified = [oc for oc in outcomes if oc.decision.promoted]
        promoted_ids: List[str] = []
        if qualified:
            winner = max(qualified, key=lambda oc: oc.report.capability)
            self.registry.promote(winner.candidate, winner.report)
            self.halflife.on_promote(winner.report.capability)
            self.seal.record_success(winner.candidate, self.registry.frontier_genome)
            promoted_ids = [winner.candidate.cid]

        new_envs = poet.coevolve(self.suite, self.registry.frontier_genome, self.rng, self.policy)

        report = CycleReport(
            cycle=gen,
            half_life_state=self.halflife.state(),
            frontier_capability=self.registry.frontier_capability,
            outcomes=outcomes,
            promoted_ids=promoted_ids,
            archive_occupancy=self.archive.occupancy(),
            new_environments=len(new_envs),
            notes={
                "shortcut_aversion": self.seal.shortcut_aversion,
                "half_life_action": self.halflife.action(),
                "new_environment_names": new_envs,
            },
        )

        if self.runpack_dir is not None:
            self.runpack_dir.mkdir(parents=True, exist_ok=True)
            path = self.runpack_dir / f"cycle_{gen}.runpack.yaml"
            runpack_exporter.export(report, self.policy.data, self.seed, path)
            report.notes["runpack"] = str(path)

        self.generation += 1
        return report

    def run(self, n_cycles: int) -> List[CycleReport]:
        return [self.run_cycle() for _ in range(n_cycles)]
