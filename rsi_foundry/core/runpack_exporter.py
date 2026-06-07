"""RunPack export/replay: reproducible records of a recursive cycle.

A RunPack freezes everything needed to understand and reproduce a cycle: the seed,
a snapshot of the governing policy, the frontier before/after, every candidate's
gate verdicts, and the half-life state. It is written as YAML via the bundled
mini-serializer (no third-party dependency). ``replay`` reloads a pack and returns
a structured summary, so a recorded run can be re-inspected deterministically.
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict

from . import _miniyaml
from .types import CycleReport


def build(cycle: CycleReport, policy_snapshot: Dict[str, Any], seed: int) -> Dict[str, Any]:
    advanced = set(cycle.promoted_ids)
    candidates = []
    for oc in cycle.outcomes:
        candidates.append({
            "cid": oc.candidate.cid,
            "origin": oc.candidate.origin,
            "lineage_hash": oc.candidate.lineage_hash,
            "claim": oc.candidate.claim.feature,
            "capability": oc.report.capability,
            "drift": oc.report.capability_drift,
            "risk": oc.report.risk,
            "novelty": oc.report.novelty_score,
            "qualified": oc.decision.promoted,            # passed every gate
            "promoted": oc.candidate.cid in advanced,     # actually advanced the frontier
            "verdict": oc.decision.reason,
            "gates": [{"name": g.name, "passed": g.passed} for g in oc.decision.gates],
        })
    return {
        "runpack_version": 1,
        "cycle": cycle.cycle,
        "seed": seed,
        "half_life_state": cycle.half_life_state,
        "frontier_capability": round(cycle.frontier_capability, 6),
        "promoted": list(cycle.promoted_ids),
        "archive_occupancy": cycle.archive_occupancy,
        "new_environments": cycle.new_environments,
        "policy": policy_snapshot,
        "candidates": candidates,
    }


def export(cycle: CycleReport, policy_snapshot: Dict[str, Any], seed: int,
           path: "pathlib.Path | str") -> Dict[str, Any]:
    pack = build(cycle, policy_snapshot, seed)
    text = _miniyaml.dumps(pack) + "\n"
    pathlib.Path(path).write_text(text)
    return pack


def replay(path: "pathlib.Path | str") -> Dict[str, Any]:
    data = _miniyaml.loads(pathlib.Path(path).read_text())
    promoted = [c for c in data.get("candidates", []) if c.get("promoted")]
    return {
        "cycle": data.get("cycle"),
        "seed": data.get("seed"),
        "half_life_state": data.get("half_life_state"),
        "n_candidates": len(data.get("candidates", [])),
        "n_promoted": len(promoted),
        "promoted_ids": [c["cid"] for c in promoted],
        "frontier_capability": data.get("frontier_capability"),
    }
