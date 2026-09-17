from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from copy import copy

from src.mod.data.ast_ import ASTNode
from src.mod.data.traits.base import BaseTrait

if TYPE_CHECKING:
    from src.mod.data.types import BaseType


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
