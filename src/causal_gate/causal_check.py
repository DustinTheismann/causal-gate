"""The adversarial mechanism-attribution check.

This module is the whole experiment. It contains **no reference to any specific
planted exploit or privileged feature** -- the test suite asserts this by
inspecting the source. It only knows how to do two general things, given a
*claimed* feature/mechanism:

1. ``attribution_holds`` -- ablate (permute) the claimed feature and check
   whether the modification's score gain *disappears*. If the gain survives the
   ablation of the claimed mechanism, the gain came from somewhere else, so the
   causal claim is false. This is permutation-importance applied to a stated
   cause: "if it's load-bearing, knocking it out should bring the structure
   down."

2. ``invariance_holds`` -- re-measure the gain across a family of environments in
   which spurious correlations are re-randomized. A genuine causal mechanism
   keeps paying off; a spurious mechanism's gain collapses (or reverses) once the
   correlation it rode on is broken. This is what catches an exploit even when
   the modification *honestly* names it -- and it generalizes to exploits the
   check has never been told about.

Both properties are stated only in terms of "the claimed feature" and "the
world's environments". The module names no feature of the world directly.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List

from .task import Dataset, Model, score


def permute_feature(dataset: Dataset, feature: str, rng: random.Random) -> Dataset:
    """Return a copy of ``dataset`` with ``feature``'s values shuffled.

    Shuffling breaks any relationship between the feature and the label (and
    between the feature and the other features) while preserving its marginal
    distribution -- the standard way to ablate a mechanism without retraining.
    If no example carries the feature, the permutation is a harmless no-op (a
    fabricated claim about an unused mechanism thus ablates to nothing).
    """
    values = [features.get(feature) for features, _ in dataset]
    present = [v for v in values if v is not None]
    rng.shuffle(present)

    out: Dataset = []
    it = iter(present)
    for features, label in dataset:
        new_features = dict(features)
        if feature in new_features:
            new_features[feature] = next(it)
        out.append((new_features, label))
    return out


@dataclass
class AttributionResult:
    holds: bool
    gain: float
    gain_after_ablation: float
    attributed: float  # how much of the gain vanished when the claim was ablated
    attributed_fraction: float


def attribution_holds(
    baseline: Model,
    modified: Model,
    dataset: Dataset,
    claimed_feature: str,
    rng: random.Random,
    threshold: float = 0.5,
    repeats: int = 5,
) -> AttributionResult:
    """Does the claimed mechanism actually carry the modification's gain?

    We compare modified-vs-baseline gain before and after permuting the claimed
    feature. If the claim is true, removing the feature should erase the gain
    (``gain_after_ablation`` ~ 0). If the gain survives, the real cause lies
    elsewhere and the claim is false.

    ``attributed_fraction`` is the fraction of the gain that the claimed
    mechanism is responsible for; the claim ``holds`` when at least ``threshold``
    of the gain is destroyed by ablating it.
    """
    gain = score(modified, dataset) - score(baseline, dataset)

    # Average over several permutations to keep the estimate stable.
    ablated_gains: List[float] = []
    for _ in range(repeats):
        ablated = permute_feature(dataset, claimed_feature, rng)
        ablated_gains.append(score(modified, ablated) - score(baseline, ablated))
    gain_after = sum(ablated_gains) / len(ablated_gains)

    attributed = gain - gain_after
    denom = gain if abs(gain) > 1e-9 else 1e-9
    fraction = attributed / denom
    holds = (gain > 0.0) and (fraction >= threshold)
    return AttributionResult(
        holds=holds,
        gain=gain,
        gain_after_ablation=gain_after,
        attributed=attributed,
        attributed_fraction=fraction,
    )


@dataclass
class InvarianceResult:
    holds: bool
    gains: List[float]
    min_gain: float
    mean_gain: float


def invariance_holds(
    baseline: Model,
    modified: Model,
    environments: List[Dataset],
    margin: float = 0.02,
) -> InvarianceResult:
    """Does the gain survive when spurious correlations are re-randomized?

    A causal mechanism keeps paying off across environments; a spurious
    mechanism's gain turns negative in environments where the correlation it
    exploited is weak or flipped. The claim is invariant only if the gain stays
    above ``margin`` in *every* environment.
    """
    gains = [score(modified, env) - score(baseline, env) for env in environments]
    min_gain = min(gains) if gains else 0.0
    mean_gain = (sum(gains) / len(gains)) if gains else 0.0
    holds = bool(gains) and min_gain >= margin
    return InvarianceResult(
        holds=holds, gains=gains, min_gain=min_gain, mean_gain=mean_gain
    )
