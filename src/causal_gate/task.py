"""The simulated benchmark world.

The world has exactly one *causal* feature, ``true_signal``: the label is
``y = 1 if true_signal > 0 else 0`` in every environment. Any other feature is
*spurious* -- it may be correlated with the label in a particular environment,
but that correlation is not part of the causal law and is free to change.

A ``Task`` exposes:

* ``benchmark()`` -- the single dataset the benchmark scores against. Here the
  spurious features are *strongly* correlated with the label, so a model that
  leans on a shortcut looks excellent.
* ``environments(...)`` -- a family of datasets that keep the causal law fixed
  but re-randomize every spurious correlation (different strength, often flipped
  sign). A genuinely causal mechanism keeps working across them; a shortcut does
  not.

Crucially, the Task is the *ground-truth world*. It knows which feature is
causal. The gate (see ``causal_check.py``) does not: it only ever asks the world
for environments and probes the mechanism the modification *claims*.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

# A single example is (feature_vector, label).
Example = Tuple[Dict[str, float], int]
Dataset = List[Example]

CAUSAL_FEATURE = "true_signal"


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class Model:
    """A trivially simple linear-threshold "model".

    It reads a weighted combination of named features and predicts class 1 when
    the weighted sum is positive. A "code change" in this toy is just a different
    set of feature weights.
    """

    weights: Dict[str, float] = field(default_factory=dict)

    def predict_one(self, features: Dict[str, float]) -> int:
        s = 0.0
        for name, w in self.weights.items():
            s += w * features.get(name, 0.0)
        return 1 if s > 0.0 else 0

    def predict(self, dataset: Dataset) -> List[int]:
        return [self.predict_one(f) for f, _ in dataset]

    def reads(self, feature: str) -> bool:
        return abs(self.weights.get(feature, 0.0)) > 1e-12


def score(model: Model, dataset: Dataset) -> float:
    """Benchmark score = accuracy over the dataset."""
    if not dataset:
        return 0.0
    correct = 0
    for features, label in dataset:
        if model.predict_one(features) == label:
            correct += 1
    return correct / len(dataset)


class Task:
    """A scored task with a true causal signal and exploitable shortcut features.

    Parameters
    ----------
    shortcut_features:
        Names of spurious features that exist in the world. In the benchmark
        environment each is strongly aligned with the label (``benchmark_corr``).
        Across counterfactual environments their alignment is re-randomized.
    n:
        Number of examples per dataset.
    seed:
        Base RNG seed (all generation is deterministic given the seed).
    benchmark_corr:
        Correlation between each shortcut and the label in the benchmark env.
    """

    def __init__(
        self,
        shortcut_features: List[str] | None = None,
        n: int = 600,
        seed: int = 0,
        benchmark_corr: float = 0.92,
    ) -> None:
        self.shortcut_features = list(
            shortcut_features if shortcut_features is not None else ["shortcut"]
        )
        self.n = n
        self.seed = seed
        self.benchmark_corr = benchmark_corr

    # -- world generation ---------------------------------------------------
    def _make_dataset(self, seed: int, shortcut_corr: Dict[str, float]) -> Dataset:
        rng = random.Random(seed)
        data: Dataset = []
        for _ in range(self.n):
            ts = rng.uniform(-1.0, 1.0)
            # The causal law -- identical in every environment.
            y = 1 if ts > 0.0 else 0
            sign = 2 * y - 1  # -1 or +1
            features: Dict[str, float] = {CAUSAL_FEATURE: ts}
            # A pure distractor: never correlated with the label anywhere.
            features["noise"] = rng.uniform(-1.0, 1.0)
            for name in self.shortcut_features:
                corr = shortcut_corr.get(name, 0.0)
                val = corr * sign + (1.0 - abs(corr)) * rng.uniform(-1.0, 1.0)
                features[name] = _clip(val)
            data.append((features, y))
        return data

    def benchmark(self) -> Dataset:
        """The dataset the benchmark gate scores against."""
        corr = {name: self.benchmark_corr for name in self.shortcut_features}
        return self._make_dataset(self.seed, corr)

    def environments(self, n_envs: int = 6, seed: int | None = None) -> List[Dataset]:
        """Counterfactual environments: causal law fixed, spurious corr resampled.

        The shortcut correlations are spread across negative and positive values
        (including sign flips) so that a model leaning on any shortcut will be
        right in some environments and badly wrong in others. The causal feature
        keeps determining the label everywhere.
        """
        base_seed = self.seed + 1000 if seed is None else seed
        envs: List[Dataset] = []
        for i in range(n_envs):
            rng = random.Random(base_seed + i)
            corr = {}
            for name in self.shortcut_features:
                # Span [-0.9, 0.9]; guarantees adversarial (negative) envs.
                corr[name] = rng.uniform(-0.9, 0.9)
            envs.append(self._make_dataset(base_seed + i, corr))
        return envs
