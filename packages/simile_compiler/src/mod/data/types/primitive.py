from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type, ClassVar

from src.mod.data.traits import (
    BaseTrait,
    OrderableTrait,
    IterableTrait,
    LiteralTrait,
    MinTrait,
    MaxTrait,
    SizeTrait,
    EmptyTrait,
    UniqueTrait,
    DomainTrait,
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

    def base_traits(self) -> set[BaseTrait]:
        return {LiteralTrait(value=None)}


@dataclass
class StringType(BaseType):
    compatible_traits: ClassVar[set[Type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        DomainTrait,
        EmptyTrait,
        SizeTrait,
        UniqueTrait,
        IterableTrait,
        OrderableTrait,
    }

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, StringType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, StringType)

    def base_traits(self) -> set[BaseTrait]:
        return {IterableTrait(), OrderableTrait()}


@dataclass
class IntType(BaseType):
    compatible_traits: ClassVar[set[Type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        DomainTrait,
        MinTrait,
        MaxTrait,
        SizeTrait,
        OrderableTrait,
    }

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, IntType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, IntType) or isinstance(other, FloatType)

    def base_traits(self) -> set[BaseTrait]:
        return {OrderableTrait()}

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

    def int_divide(self, other: BaseType) -> IntType:
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

    def divide(self, other: BaseType) -> FloatType:
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
    def upto(self, other: BaseType) -> SetType:
        from src.mod.data.types.set_ import SetType

        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return SetType(element_type=IntType())


@dataclass
class FloatType(BaseType):
    compatible_traits: ClassVar[set[Type[BaseTrait]]] = IntType.compatible_traits

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, FloatType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, FloatType)

    def base_traits(self) -> set[BaseTrait]:
        return {OrderableTrait()}

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

    def divide(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def multiply(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def power(self, other: BaseType) -> FloatType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))
        return FloatType()

    def int_divide(self, other: BaseType) -> IntType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return IntType()

    def modulo(self, other: BaseType) -> IntType:
        self._is_subtype_or_error(other, (IntType(), FloatType()))

        return IntType()
