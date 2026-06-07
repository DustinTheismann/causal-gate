"""Novelty scoring + MAP-Elites quality-diversity archive (anti-collapse)."""

from rsi_foundry.loops.novelty_ledger import NoveltyLedger

from conftest import make_candidate, make_report


def _consider(ledger, genome, descriptor, capability, cid="c"):
    cand = make_candidate(genome, "coding")
    cand.cid = cid
    rep = make_report(capability=capability, descriptor=descriptor)
    return ledger.consider(cand, rep)


def test_empty_ledger_is_maximally_novel():
    led = NoveltyLedger()
    assert led.novelty({"coding": 0.5}, ("coding", "none", 2)) == 1.0


def test_near_duplicate_has_low_novelty():
    led = NoveltyLedger()
    _consider(led, {"coding": 0.9, "reasoning": 0.1}, ("coding", "none", 3), 0.6)
    far = led.novelty({"reasoning": 0.9, "coding": 0.0}, ("reasoning", "none", 4))
    near = led.novelty({"coding": 0.9, "reasoning": 0.1}, ("coding", "none", 3))
    assert far > near


def test_map_elites_keeps_best_per_niche():
    led = NoveltyLedger()
    niche = ("coding", "none", 3)
    assert _consider(led, {"coding": 0.7}, niche, 0.5, "a") is True
    assert _consider(led, {"coding": 0.8}, niche, 0.7, "b") is True   # better -> replaces
    assert _consider(led, {"coding": 0.75}, niche, 0.6, "c") is False  # worse -> kept out
    assert led.elites[niche].cid == "b"
    assert led.occupancy() == 1  # still one niche


def test_distinct_niches_grow_occupancy():
    led = NoveltyLedger()
    _consider(led, {"coding": 0.7}, ("coding", "none", 3), 0.5, "a")
    _consider(led, {"planning": 0.7}, ("planning", "none", 3), 0.55, "b")
    _consider(led, {"retrieval": 0.7}, ("retrieval", "low", 3), 0.52, "c")
    assert led.occupancy() == 3
    assert led.best().cid == "b"  # highest capability across niches
