"""Real code-improvement demonstration.

Run:  python examples/run_code_improvement.py

Shows the foundry taking a deliberately-wrong seed program to one that passes real
unit tests, by a sequence of single-hole edits each justified by the causal-by-revert
gate; then the meta-loop selecting a cheaper improver policy by real measurement.
Everything here executes actual generated Python in a sandboxed subprocess.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rsi_foundry.code import meta, tasks
from rsi_foundry.code.code_foundry import CodeFoundry
from rsi_foundry.code.synthesis import Strategy


def main() -> None:
    learned = Strategy("lazy", lazy_causal=True, tie_break_bandit=True)

    print("== Real program synthesis under governance ==\n")
    for task in tasks.all_tasks():
        f = CodeFoundry(task, learned, seed=0)
        result = f.solve(budget=30)
        print(f"task `{task.name}`: solved={result.solved} in {result.cycles} edits, "
              f"{result.evals} real executions")
        for s in result.history:
            print(f"    edit {s.hole} -> {s.value}  | visible pass-rate {s.visible_rate} "
                  f"| causal attribution {s.attributed_fraction}")
        print("    final program:")
        for line in result.source.rstrip().splitlines():
            print("      " + line)
        print()

    print("== Meta self-improvement (the loop improves its own improver) ==\n")
    incumbent = Strategy("baseline", lazy_causal=False, tie_break_bandit=False)
    candidates = [learned, Strategy("lazy_only", lazy_causal=True, tie_break_bandit=False)]
    train = [tasks.get_task("clamp"), tasks.get_task("count_positive")]
    validate = [tasks.get_task("sign")]
    res = meta.search(incumbent, candidates, train, validate)
    for name, sc in res.scores.items():
        print(f"  strategy {name:12} -> {sc.total_evals} executions, solves all = {sc.solved_all}")
    print(f"\n  {res.reason}")
    print(f"  validated on held-out task: solved={res.validate_solved} "
          f"({res.validate_evals} executions)")


if __name__ == "__main__":
    main()
