from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import ClassVar, Type

from src.mod.data.types.base import _TraitMixin, BaseType
from src.mod.data.traits import (
    BaseTrait,
    OrderableTrait,
    IterableTrait,
    LiteralTrait,
    DomainTrait,
    MinTrait,
    MaxTrait,
    SizeTrait,
    ImmutableTrait,
    TotalOnDomainTrait,
    TotalOnRangeTrait,
    ManyToOneTrait,
    OneToManyTrait,
    EmptyTrait,
    TotalTrait,
    UniqueTrait,
    Traits,
)
from src.mod.data.types.typing_rule_decorator import typing_rule


@dataclass
class TupleType(BaseType):
    items: list[BaseType]
    compatible_traits: ClassVar[set[Type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        DomainTrait,
        MinTrait,
        MaxTrait,
        SizeTrait,
        UniqueTrait,
        TotalTrait,
        IterableTrait,
        OrderableTrait,
        EmptyTrait,
    }

    def __post__init__(self):
        for item in self.items:
            if not isinstance(item, BaseType):
                raise TypeError(f"TupleType items must be BaseType instances, got {type(item)}")

    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, TupleType):
            return False
        if len(self.items) != len(other.items):
            return False

        for self_item, other_item in zip(self.items, other.items):
            if not self_item._is_eq_type(other_item):
                return False
        return True

    @typing_rule("Sub Product")
    def _is_subtype(self, other: BaseType) -> bool:
        if not isinstance(other, TupleType):
            return False
        if len(self.items) != len(other.items):
            return False

        for self_item, other_item in zip(self.items, other.items):
            if not self_item.is_subtype(other_item):
                return False
        return True

    def _is_sub_traits(self, other: _TraitMixin) -> bool:
        empty_traits = self.traits.find(EmptyTrait)
        if empty_traits is not None:
            return True
        raise NotImplementedError

    def base_traits(self) -> set[BaseTrait]:
        return {IterableTrait()}

    @classmethod
    def enumeration(cls, element_types: list[BaseType]) -> TupleType:
        """Create a set from an enumeration of elements of a specific type."""
        if element_types == []:
            return cls(items=[])

        return cls(items=element_types)


@dataclass
class PairType(TupleType):

    def __init__(self, left: BaseType, right: BaseType, *, traits: Traits | None = None) -> None:
        if traits is None:
            traits = Traits()

        super().__init__(items=[left, right], traits=traits)

    def base_traits(self) -> set[BaseTrait]:
        return {*super().base_traits(), SizeTrait(2)}

    @property
    def left(self) -> BaseType:
        return self.items[0]

    @property
    def right(self) -> BaseType:
        return self.items[1]

    @classmethod
    def maplet(cls, key_type: BaseType, value_type: BaseType) -> PairType:
        """Create a PairType representing a maplet from key_type to value_type."""
        return cls(left=key_type, right=value_type)
