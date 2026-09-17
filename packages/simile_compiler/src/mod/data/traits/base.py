from __future__ import annotations
from dataclasses import dataclass

# These must be hash-safe
SimileLiteralAsPythonOrderable = int | float | str | tuple
SimileLiteralAsPython = bool | SimileLiteralAsPythonOrderable | frozenset | None


@dataclass(frozen=True)
class BaseTrait:
    pass


@dataclass(frozen=True)
class ImmutableTrait(BaseTrait):
    pass


@dataclass(frozen=True)
class LiteralTrait(BaseTrait):
    value: SimileLiteralAsPython


@dataclass(frozen=True)
class UndefinedTrait(BaseTrait):
    pass
