"""Real sandboxed execution of generated code against real unit tests.

A candidate's source is rendered to a string and executed in an *isolated*
subprocess (`python -I`) with a CPU-time rlimit and a wall-clock timeout, fed the
tests over stdin as JSON and returning per-test pass/fail as JSON. Before anything
runs, a static safety scan rejects source that reaches outside the language
sandbox (imports, file/exec/eval, dunder access). This is the real containment
boundary -- nothing is scored without surviving it.

No third-party dependency; the harness is a self-contained program string.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

from .tasks import Test

_FORBIDDEN = (
    "import", "__", "open(", "eval(", "exec(", "compile(",
    "globals(", "locals(", "getattr(", "setattr(", "input(",
    "os.", "sys.", "subprocess", "socket", "pathlib", "shutil",
)

_HARNESS = r"""
import json, sys, resource
try:
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
except Exception:
    pass
data = json.load(sys.stdin)
ns = {}
try:
    exec(data["source"], ns)
    fn = ns[data["entry"]]
except Exception as e:
    print(json.dumps({"compile_error": repr(e)}))
    sys.exit(0)
results = []
for t in data["tests"]:
    try:
        out = fn(*t["input"])
        results.append(bool(out == t["expected"]))
    except Exception:
        results.append(False)
print(json.dumps({"results": results}))
"""


@dataclass
class ExecResult:
    results: List[bool]
    n_total: int
    timed_out: bool = False
    error: Optional[str] = None
    violation: Optional[str] = None

    @property
    def n_pass(self) -> int:
        return sum(self.results)

    @property
    def pass_rate(self) -> float:
        return self.n_pass / self.n_total if self.n_total else 0.0

    @property
    def ok(self) -> bool:
        """Executed cleanly inside the sandbox (no violation/timeout/compile error)."""
        return self.violation is None and not self.timed_out and self.error is None


def safety_scan(source: str) -> Optional[str]:
    for token in _FORBIDDEN:
        if token in source:
            return f"forbidden token `{token}`"
    return None


def run(source: str, entry: str, tests: List[Test], timeout: float = 5.0) -> ExecResult:
    n = len(tests)
    violation = safety_scan(source)
    if violation is not None:
        return ExecResult([False] * n, n, violation=violation)

    payload = json.dumps({
        "source": source,
        "entry": entry,
        "tests": [{"input": list(args), "expected": expected} for args, expected in tests],
    })
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _HARNESS],
            input=payload, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ExecResult([False] * n, n, timed_out=True)

    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return ExecResult([False] * n, n, error=(proc.stderr or "no output")[:200])

    if "compile_error" in data:
        return ExecResult([False] * n, n, error=data["compile_error"])
    results = [bool(b) for b in data.get("results", [])]
    if len(results) != n:
        results = (results + [False] * n)[:n]
    return ExecResult(results, n)
