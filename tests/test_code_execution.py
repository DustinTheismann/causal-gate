"""Real sandboxed execution: the benchmark actually runs generated code."""

from rsi_foundry.code import execution, tasks


def test_correct_filling_passes_all_real_tests():
    t = tasks.get_task("clamp")
    res = execution.run(t.render(t.correct), t.entry, t.visible + t.held)
    assert res.ok and res.pass_rate == 1.0


def test_seed_filling_fails_some_tests():
    t = tasks.get_task("clamp")
    res = execution.run(t.render(t.seed), t.entry, t.visible)
    assert res.ok and res.pass_rate < 1.0


def test_forbidden_import_is_a_containment_violation():
    res = execution.run("def solve(x):\n    import os\n    return os.getpid()", "solve", [([1], 1)])
    assert not res.ok and res.violation is not None


def test_runaway_code_is_contained():
    res = execution.run("def solve(x):\n    while True:\n        pass\n", "solve", [([1], 1)], timeout=3)
    # Killed by CPU rlimit or wall timeout -- either way it does not pass and is not "ok".
    assert not res.ok and res.pass_rate == 0.0


def test_exception_in_candidate_counts_as_failures_not_crash():
    res = execution.run("def solve(x):\n    return x[0]\n", "solve", [([5], 5)])
    assert res.ok and res.pass_rate == 0.0  # TypeError per test -> recorded as fail
