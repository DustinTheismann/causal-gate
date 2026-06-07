"""Real code-improvement substrate: generation, execution, learning, meta.

Swaps the simulated genome proposers and scoring-function benchmark for actual
program synthesis executed against actual unit tests, with real learning from
execution feedback and a meta-loop that improves the improver itself.
"""

from .tasks import all_tasks, get_task, SketchTask
from .synthesis import Strategy
from .code_foundry import CodeFoundry, SolveResult
from . import meta

__all__ = ["all_tasks", "get_task", "SketchTask", "Strategy",
           "CodeFoundry", "SolveResult", "meta"]
