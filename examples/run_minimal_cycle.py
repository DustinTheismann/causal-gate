"""Minimal end-to-end demonstration of the Recursive R&D Foundry.

Run:  python examples/run_minimal_cycle.py

Shows, per cycle: the capability frontier, the HALF-LIFE state, which successor
was promoted, how many MAP-Elites niches are filled, whether POET spawned a harder
environment, and the SEAL shortcut-aversion the foundry has learned from rejecting
reward hacks. Writes a reproducible RunPack to runpacks/minimal_cycle.runpack.yaml.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rsi_foundry import Foundry
from rsi_foundry.core import runpack_exporter

RUNPACKS = pathlib.Path(__file__).resolve().parents[1] / "runpacks"


def main() -> None:
    foundry = Foundry(seed=0)

    print(f"seed agent capability: {foundry.registry.frontier_capability:.4f}\n")
    header = f"{'cyc':>3} {'frontier':>9} {'state':>6} {'promoted':<16} {'niches':>6} {'envs':>5} {'aversion':>8}"
    print(header)
    print("-" * len(header))

    for i in range(8):
        rep = foundry.run_cycle()
        if i == 0:  # freeze a stable sample RunPack
            runpack_exporter.export(
                rep, foundry.policy.data, foundry.seed, RUNPACKS / "minimal_cycle.runpack.yaml"
            )
        promoted = rep.promoted_ids[0] if rep.promoted_ids else "-"
        print(
            f"{rep.cycle:>3} {rep.frontier_capability:>9.4f} {rep.half_life_state:>6} "
            f"{promoted:<16} {rep.archive_occupancy:>6} {rep.new_environments:>5} "
            f"{rep.notes['shortcut_aversion']:>8.2f}"
        )

    print("\nWhat to notice:")
    print("  * the frontier rises only through gate-passing successors, then plateaus")
    print("    once governed improvements run out -- not unbounded self-improvement;")
    print("  * shortcut-aversion climbs as the causal/containment gates reject reward")
    print("    hacks, and the DGM loop stops proposing them (SEAL self-training);")
    print("  * POET spawns harder environments once the frontier masters the suite;")
    print(f"  * a RunPack was written to {RUNPACKS / 'minimal_cycle.runpack.yaml'}")


if __name__ == "__main__":
    main()
