from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from copy import copy

from src.mod.data.ast_ import ASTNode

if TYPE_CHECKING:
    from src.mod.data.types import BaseType

# These must be hash-safe
SimileLiteralAsPythonOrderable = int | float | str | tuple
SimileLiteralAsPython = bool | SimileLiteralAsPythonOrderable | set | None


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


@dataclass(frozen=True)
class GenericBoundTrait(BaseTrait):
    bound_types: tuple[BaseType, ...]  # can have multiple of the same trait here - multiple generic bounds mean a type union

    def merge_copy(self, other: GenericBoundTrait) -> GenericBoundTrait:
        # combine the bound types of both traits
        combined_bound_types = copy(list(self.bound_types))
        for other_bound_type in other.bound_types:
            if other_bound_type not in self.bound_types:
                combined_bound_types.append(other_bound_type)
        return GenericBoundTrait(bound_types=tuple(combined_bound_types))
