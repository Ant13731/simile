from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import ClassVar, Type

from src.mod.data.types.base import BaseType
from src.mod.data.types.traits import (
    Trait,
    TraitCollection,
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
    UniqueElementsTrait,
)


@dataclass
class TupleType(BaseType):
    items: tuple[BaseType, ...]
    valid_traits: ClassVar[set[Type[Trait]]] = {
        *BaseType.valid_traits,
        MinTrait,
        MaxTrait,
        SizeTrait,
        UniqueElementsTrait,
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

    def _is_subtype(self, other: BaseType) -> bool:
        if not isinstance(other, TupleType):
            return False
        if len(self.items) != len(other.items):
            return False

        for self_item, other_item in zip(self.items, other.items):
            if not self_item._is_subtype(other_item):
                return False
        return True

    def _is_sub_traits(self, other: BaseType) -> bool:
        if self.trait_collection.empty_trait is not None:
            return True
        raise NotImplementedError

    def _populate_mandatory_traits(self) -> None:
        self.trait_collection.iterable_trait = IterableTrait()

    @classmethod
    def enumeration(cls, element_types: list[BaseType]) -> TupleType:
        """Create a set from an enumeration of elements of a specific type."""
        if element_types == []:
            return cls(items=())

        return cls(items=tuple(element_types))


@dataclass
class PairType(TupleType):

    def __init__(self, left: BaseType, right: BaseType, *, trait_collection: TraitCollection | None = None) -> None:
        if trait_collection is None:
            trait_collection = TraitCollection()

        super().__init__(items=(left, right), trait_collection=trait_collection)

    def _populate_mandatory_traits(self) -> None:
        super()._populate_mandatory_traits()
        self.trait_collection.size_trait = SizeTrait(2)

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
