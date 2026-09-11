from dataclasses import dataclass

from src.mod.data.ast_ import ASTNode
from src.mod.data.traits.base import BaseTrait, SimileLiteralAsPython


@dataclass(frozen=True)
class DomainTrait(BaseTrait):
    values: frozenset[SimileLiteralAsPython]

    # def __init__(self, values: list[SimileLiteralAsPython]):
    #     super().__init__()
    #     # TODO could also cast things to hashable item types and then let type(values) == set.
    #     # Ex. set items -> frozenset, frozendict, list -> tuple, ...
    #     deduped_values = []
    #     for value in values:
    #         if value not in deduped_values:
    #             deduped_values.append(value)
    #     setattr(self, "values", deduped_values)

    def get_value_type(self) -> type:
        if not self.values:
            raise ValueError("Cannot determine value type of empty domain")
        value_type = type(next(iter(self.values)))
        for value in self.values:
            # Widen types as needed (for now only widen int->float)
            if value_type is int and type(value) == float:
                value_type = float

            if value_type != type(value):
                raise ValueError(f"DomainTrait values must all be of the same (python) type, but found {value_type} and {type(value)} in {self.values}")
        return value_type


@dataclass(frozen=True)
class IterableTrait(BaseTrait):
    pass


@dataclass(frozen=True)
class UniqueTrait(BaseTrait):
    pass


@dataclass(frozen=True)
class EmptyTrait(BaseTrait):
    pass


@dataclass(frozen=True)
class SizeTrait(BaseTrait):
    size: int


@dataclass(frozen=True)
class TotalTrait(BaseTrait):
    pass
