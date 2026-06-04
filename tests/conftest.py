"""Shared fixtures: one world, one baseline model.

The baseline reads the causal feature only weakly and is dominated by a pure
distractor, so it is deliberately mediocre -- leaving real room for improvement.
"""

import pytest

from causal_gate import Model, Task

BASELINE_WEIGHTS = {"true_signal": 0.4, "noise": 1.0}


@pytest.fixture
def task():
    return Task()


@pytest.fixture
def baseline():
    return Model(dict(BASELINE_WEIGHTS))
