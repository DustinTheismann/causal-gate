"""A candidate modification and the causal claim attached to it.

A ``Modification`` bundles a proposed new ``Model`` with a ``CausalClaim``: an
explicit, checkable statement of *why* the change is supposed to help -- which
feature/mechanism is claimed to carry the improvement. The whole point of the
causal gate is that this claim is adversarially tested rather than trusted.
"""

from __future__ import annotations

from dataclasses import dataclass

from .task import Model


@dataclass(frozen=True)
class CausalClaim:
    """"This modification helps *because of* ``feature``."

    ``feature`` names the mechanism the modification asserts is responsible for
    its score gain. ``mechanism`` is a human-readable restatement of the claim.
    """

    feature: str
    mechanism: str = ""

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"gain comes from `{self.feature}`" + (
            f" ({self.mechanism})" if self.mechanism else ""
        )


@dataclass
class Modification:
    """A proposed code change (here: new model weights) plus its causal claim."""

    name: str
    model: Model
    claim: CausalClaim
