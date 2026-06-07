"""POET-style environment coevolution: the benchmark hardens with the frontier."""

import random

from rsi_foundry.connectors.benchmark_adapters import BenchmarkSuite, baseline_genome
from rsi_foundry.core.policy import Policy
from rsi_foundry.evals import poet


def _master_genome():
    return {"reasoning": 0.95, "coding": 0.95, "retrieval": 0.95, "planning": 0.95, "shortcut": 0.0}


def test_weak_frontier_spawns_nothing():
    suite, policy = BenchmarkSuite(), Policy.load()
    spawned = poet.coevolve(suite, baseline_genome(), random.Random(0), policy)
    assert spawned == [] and len(suite.tasks) == 5


def test_mastered_suite_spawns_a_harder_task():
    suite, policy = BenchmarkSuite(), Policy.load()
    before = len(suite.tasks)
    hardest_before = max(t.difficulty for t in suite.tasks)
    spawned = poet.coevolve(suite, _master_genome(), random.Random(1), policy)
    assert len(spawned) == 1 and len(suite.tasks) == before + 1
    assert suite.tasks[-1].difficulty >= hardest_before


def test_spawning_is_capped():
    policy = Policy.load()
    suite = BenchmarkSuite()
    cap = policy.get("poet.max_environments")
    rng = random.Random(2)
    for _ in range(cap + 10):
        poet.coevolve(suite, _master_genome(), rng, policy)
    assert len(suite.tasks) <= cap
