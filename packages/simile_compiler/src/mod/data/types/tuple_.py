from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import ClassVar, Type

from src.mod.data.types.base import _TraitMixin, BaseType
from src.mod.data.types.error import SimileTypeError
from src.mod.data.types.meta import GenericType
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
        raise NotImplementedError("Sub traits not implemented for tuple type")

    def base_traits(self) -> set[BaseTrait]:
        return {IterableTrait()}

    @classmethod
    def enumeration(cls, element_types: list[BaseType]) -> TupleType:
        """Create a set from an enumeration of elements of a specific type."""
        if element_types == []:
            return cls(items=[])

        return cls(items=element_types)

    def match_generic_types(self, concrete_type: BaseType) -> dict[tuple[int, int], BaseType]:
        if not isinstance(concrete_type, TupleType):
            raise SimileTypeError(f"Cannot match generic types for TupleType with non-TupleType {concrete_type} (self is {self})")
        if len(concrete_type.items) != len(self.items):
            raise SimileTypeError(f"Generic type match for tuple called with incorrect number of elements. Expected {len(self.items)}, got {len(concrete_type.items)}")

        generic_to_concrete_types: dict[tuple[int, int], BaseType] = {}
        for concrete_arg_type, possible_generic_arg_type in zip(concrete_type.items, self.items):
            generic_to_concrete_arg_types = possible_generic_arg_type.match_generic_types(concrete_arg_type)
            for generic_id, concrete_arg_nested_type in generic_to_concrete_arg_types.items():
                if generic_id in generic_to_concrete_types:
                    previously_provided_type = generic_to_concrete_types[generic_id]
                    max_provided_type = BaseType.max_type([concrete_arg_nested_type, previously_provided_type])
                    generic_to_concrete_types[generic_id] = max_provided_type
                    continue

                generic_to_concrete_types[generic_id] = concrete_arg_nested_type

        return generic_to_concrete_types

    def replace_generic_types(self, generic_to_concrete_type_map: dict[tuple[int, int], BaseType]) -> BaseType:
        new_items = [item.replace_generic_types(generic_to_concrete_type_map) for item in self.items]
        return type(self)(items=new_items, traits=self.traits)

    def extract_generic_types(self) -> list[GenericType]:
        generic_types: list[GenericType] = []
        for item in self.items:
            generic_types.extend(item.extract_generic_types())
        return generic_types


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

    def replace_generic_types(self, generic_to_concrete_type_map: dict[tuple[int, int], BaseType]) -> BaseType:
        new_items = [item.replace_generic_types(generic_to_concrete_type_map) for item in self.items]
        assert len(new_items) == 2
        return type(self)(*new_items, traits=self.traits)
