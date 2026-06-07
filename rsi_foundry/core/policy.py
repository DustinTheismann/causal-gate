"""Typed access to the governance policy (configs/policy.yaml).

Loads the YAML with the bundled mini-parser (no third-party dependency) and
exposes nested values with dotted keys. A built-in default mirrors the shipped
file so the foundry still runs if the file is absent.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any, Dict

from . import _miniyaml

_DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[2] / "configs" / "policy.yaml"

_DEFAULTS: Dict[str, Any] = {
    "promotion": {
        "fitness_delta_threshold": 0.01,
        "novelty_threshold": 0.05,
        "max_regression_failures": 0,
        "max_side_effect_scope": 0.34,
    },
    "causal_gate": {
        "attribution_threshold": 0.5,
        "invariance_margin": 0.0,
        "n_environments": 7,
    },
    "half_life": {
        "assurance_renewal": 0.15,
        "safety_factor": 1.0,
        "amber_ratio": 0.6,
        "red_ratio": 1.0,
        "black_ratio": 1.6,
    },
    "contracts": {"risk_requires_contract": 0.5},
    "poet": {"spawn_score": 0.7, "max_environments": 24},
}


@dataclass
class Policy:
    data: Dict[str, Any]

    @classmethod
    def load(cls, path: "pathlib.Path | str | None" = None) -> "Policy":
        p = pathlib.Path(path) if path else _DEFAULT_PATH
        if not p.exists():
            return cls(_deep_copy(_DEFAULTS))
        loaded = _miniyaml.loads(p.read_text()) or {}
        merged = _deep_merge(_deep_copy(_DEFAULTS), loaded)
        return cls(merged)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def _deep_copy(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: _deep_copy(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_deep_copy(v) for v in d]
    return d


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
