from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable, ClassVar, Type, TypeVar
import inspect

from src.mod.data.types.error import SimileTypeError
from src.mod.data.types.traits import Trait, TraitCollection, LiteralTrait, DomainTrait, ImmutableTrait


T = TypeVar("T", bound="BaseType")


# Primitive types
@dataclass(kw_only=True)
class BaseType:
    """Base type for all Simile types."""

    trait_collection: TraitCollection = field(default_factory=TraitCollection)

    valid_traits: ClassVar[set[Type[Trait]]] = {
        LiteralTrait,
        DomainTrait,
        ImmutableTrait,
    }
    """Any trait not within this set is invalid for this type."""

    def __post_init__(self):
        self.populate_mandatory_traits()

    # Actual type methods
    def cast(self, caster: T, add_trait_collection: TraitCollection | None = None) -> T:
        """Cast the type to a different type."""
        caster = deepcopy(caster)
        # TODO only add traits if the traits make sense to add (ex. no min trait allowed on a StringType)
        # Each type should specify which traits are allowed

        if add_trait_collection is not None:
            caster.trait_collection = self.trait_collection.merge(add_trait_collection)
        return caster

    def _allowed_traits(self) -> list[Type[Trait]]:
        """Return a list of allowed trait types for this type."""
        raise NotImplementedError

    def equals(self, other: BaseType) -> BoolType:
        """Check if this type is equal to another type."""
        raise NotImplementedError

    def not_equals(self, other: BaseType) -> BoolType:
        raise NotImplementedError

    # Helper methods
    def is_eq_type(self, other: BaseType, check_traits: bool = False) -> bool:
        from src.mod.data.types.meta import DeferToSymbolTable

        if isinstance(other, DeferToSymbolTable):
            raise SimileTypeError("Cannot compare DeferToSymbolTable types before symbol table resolution")

        if check_traits:
            return self._is_eq_type(other) and self._is_eq_traits(other)
        return self._is_eq_type(other)

    def _is_eq_type(self, other: BaseType) -> bool:
        raise NotImplementedError

    def _is_eq_traits(self, other: BaseType) -> bool:
        """Check whether the type would be equal when considering traits."""
        return self.trait_collection == other.trait_collection

    def is_subtype(self, other: BaseType, check_traits: bool = False) -> bool:
        """Check if self is a sub-type of other (in formal type theory, whether self <= other)."""
        from src.mod.data.types.meta import GenericType, AnyType_

        # Reflexive Subtype
        if self.is_eq_type(other, check_traits):
            return True

        is_sub_trait = True
        if check_traits:
            is_sub_trait = self._is_sub_traits(other)

        # Sub Top Type
        if isinstance(other, AnyType_):
            return is_sub_trait

        # Sub Top Type for generics
        if not isinstance(self, GenericType) and isinstance(other, GenericType):
            if other.trait_collection.generic_bound_trait is None:
                return is_sub_trait  # unbound generic is supertype of all types

            for other_bound in other.trait_collection.generic_bound_trait.bound_types:
                if self.is_subtype(other_bound):
                    return is_sub_trait
            return False

        return is_sub_trait and self._is_subtype(other)

    def _is_subtype(self, other: BaseType) -> bool:
        raise NotImplementedError

    def _is_sub_traits(self, other: BaseType) -> bool:
        """Check whether the type is a sub-type when considering traits."""
        raise NotImplementedError

    @classmethod
    def max_type(cls, types: list[BaseType]) -> BaseType:
        """Return the widest type among the inputs.

        Throws a SimileTypeError if types are incompatible (aside from AnyType_)."""
        class_name = cls.__name__
        method_name = inspect.stack()[1][3]

        widest_type = types[0]
        for type_ in types:
            # Widen type as necessary
            if widest_type.is_subtype(type_):
                widest_type = type_
            elif not type_.is_subtype(widest_type):
                raise SimileTypeError(
                    f"Cannot perform operation {class_name}.{method_name}: Cannot find max (widest) type with incompatible element types: {widest_type} and {type_}"
                )
        return widest_type

    @classmethod
    def min_type(cls, types: list[BaseType]) -> BaseType:
        """Return the narrowest type among the inputs.

        Throws a SimileTypeError if types are incompatible (aside from NoneType_)."""
        class_name = cls.__name__
        method_name = inspect.stack()[1][3]

        narrowest_type = types[0]
        for type_ in types:
            # Widen type as necessary
            if type_.is_subtype(narrowest_type):
                narrowest_type = type_
            elif not narrowest_type.is_subtype(type_):
                raise SimileTypeError(
                    f"Cannot perform operation {class_name}.{method_name}:Cannot find min (narrowest) type with incompatible element types: {narrowest_type} and {type_}"
                )
        return narrowest_type

    def _is_subtype_or_error(self, other: BaseType, is_subtype_of: BaseType | tuple[BaseType, ...]) -> None:
        """Helper to perform is_subtype with a SimileTypeError exception on failure"""
        class_name = self.__class__.__name__
        method_name = inspect.stack()[1][3]

        if not isinstance(is_subtype_of, tuple):
            is_subtype_of = (is_subtype_of,)

        for subtype_to_check in is_subtype_of:
            if other.is_subtype(subtype_to_check):
                return

        raise SimileTypeError(f"Cannot perform operation {class_name}.{method_name} with incompatible type: {other} (expected a (sub)type of one of {is_subtype_of})")

    def populate_mandatory_traits(self) -> None:
        self._populate_mandatory_traits()
        self.trait_collection._fill_implicit_traits()

    def _populate_mandatory_traits(self) -> None:
        raise NotImplementedError


@dataclass
class BoolType(BaseType):
    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, BoolType)

    def _is_subtype(self, other: BaseType) -> bool:
        return isinstance(other, BoolType)

    def not_(self) -> BoolType:
        return BoolType()

    def equivalent(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, BoolType())
        return BoolType()

    def not_equivalent(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, BoolType())
        return BoolType()

    def implies(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, BoolType())
        return BoolType()

    def and_(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, BoolType())
        return BoolType()

    def or_(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, BoolType())
        return BoolType()

    def _populate_mandatory_traits(self) -> None:
        from src.mod.data.ast_ import True_, False_

        self.trait_collection.domain_trait = DomainTrait(values=[True_(), False_()])
