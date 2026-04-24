from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type, ClassVar

from src.mod.data.types.error import SimileTypeError
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
from src.mod.data.types.base import BaseType, BoolType

if TYPE_CHECKING:
    from src.mod.data.types.set_ import SetType


@dataclass
class NoneType_(BaseType):
    """Intended for statements without a type, not expressions. For example, a while loop node doesn't have a type."""

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, NoneType_)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, NoneType_)

    def _populate_mandatory_traits(self) -> None:
        from src.mod.data.ast_ import None_

        self.trait_collection.literal_trait = LiteralTrait(value=None_())


@dataclass
class StringType(BaseType):
    valid_traits: ClassVar[set[Type[Trait]]] = {
        *BaseType.valid_traits,
        EmptyTrait,
        SizeTrait,
        UniqueElementsTrait,
        IterableTrait,
        OrderableTrait,
    }

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, StringType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, StringType)

    def _populate_mandatory_traits(self) -> None:
        self.iterable_trait = IterableTrait()
        self.orderable_trait = OrderableTrait()


@dataclass
class IntType(BaseType):
    valid_traits: ClassVar[set[Type[Trait]]] = {
        *BaseType.valid_traits,
        MinTrait,
        MaxTrait,
        SizeTrait,
        OrderableTrait,
    }

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, IntType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, IntType) or isinstance(other, FloatType)

    def _populate_mandatory_traits(self) -> None:
        self.trait_collection.orderable_trait = OrderableTrait()

    # Comparison
    def greater_than(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def less_than(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def greater_than_equals(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def less_than_equals(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    # Arithmetic
    def negate(self) -> IntType:
        return IntType()

    def int_division(self, other: BaseType) -> IntType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return IntType()

    def modulo(self, other: BaseType) -> IntType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return IntType()

    def add(self, other: BaseType) -> IntType | FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        if isinstance(other, FloatType):
            return other.add(self)
        return IntType()

    def subtract(self, other: BaseType) -> IntType | FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        if isinstance(other, FloatType):
            return other.subtract(self)
        return IntType()

    def division(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return FloatType()

    def multiply(self, other: BaseType) -> IntType | FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        if isinstance(other, FloatType):
            return other.multiply(self)
        return IntType()

    def power(self, other: BaseType) -> IntType | FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        if isinstance(other, FloatType):
            return other.power(self)
        return IntType()

    # Sets
    def upto(self, other: IntType) -> SetType:
        from src.mod.data.types.set_ import SetType

        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return SetType(element_type=IntType())


@dataclass
class FloatType(BaseType):
    valid_traits: ClassVar[set[Type[Trait]]] = {
        *BaseType.valid_traits,
        MinTrait,
        MaxTrait,
        SizeTrait,
        OrderableTrait,
    }

    def __post_init__(self):
        self.populate_mandatory_traits()

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, FloatType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, FloatType)

    def _populate_mandatory_traits(self) -> None:
        self.trait_collection.orderable_trait = OrderableTrait()

    def greater_than(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def less_than(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def greater_than_equals(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def less_than_equals(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return BoolType()

    def negate(self) -> FloatType:
        return FloatType()

    def add(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def subtract(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def division(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def multiply(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def power(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()
