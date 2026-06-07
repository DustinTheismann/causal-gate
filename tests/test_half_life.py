"""HALF-LIFE assurance control plane: capability must not outrun assurance."""

from rsi_foundry.governance.half_life import (
    AMBER,
    BLACK,
    GREEN,
    RED,
    HalfLifeController,
)


def _controller(frontier=0.5):
    return HalfLifeController(
        renewal=0.1, safety_factor=1.0, amber_ratio=0.6, red_ratio=1.0,
        black_ratio=1.6, frontier_capability=frontier, assured_level=frontier,
    )


def test_within_budget_promotes_in_green():
    c = _controller()
    g = c.gate(0.08)
    assert g.passed and c.state() == GREEN and g.evidence["action"] == "promote"


def test_single_over_large_jump_is_refused_even_in_green():
    c = _controller()
    assert c.state() == GREEN
    g = c.gate(0.4)  # 4x the one-period budget
    assert not g.passed and "exceeds one-period budget" in g.reason


def test_gap_escalates_states_and_constrains():
    c = _controller()
    c.on_promote(0.65)             # gap 0.15 -> ratio 1.5
    assert c.state() == RED and c.action() == "constrain"
    # Even a tiny drift is blocked while constrained.
    assert not c.gate(0.02).passed

    c.on_promote(0.72)             # gap 0.22 -> ratio 2.2
    assert c.state() == BLACK and c.action() == "freeze"


def test_renew_closes_the_gap():
    c = _controller()
    c.on_promote(0.7)              # gap 0.2 -> BLACK
    assert c.state() == BLACK
    c.renew(); c.renew()          # two renewal increments of 0.1 each
    assert c.gap == 0.0 and c.state() == GREEN


def test_amber_is_promote_but_watched():
    c = _controller()
    c.on_promote(0.57)            # gap 0.07 -> ratio 0.7 in [0.6, 1.0)
    assert c.state() == AMBER and c.gate(0.05).passed
