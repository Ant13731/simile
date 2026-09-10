from __future__ import annotations
from dataclasses import dataclass, field, fields, asdict
from copy import deepcopy
from typing import Callable, ClassVar, NoReturn, Type, TypeVar
import inspect
from loguru import logger


from src.mod.data.types.error import SimileTypeError
from src.mod.data.types.typing_rule_decorator import typing_rule
from src.mod.data.traits import (
    SimileTraitError,
    BaseTrait,
    LiteralTrait,
    DomainTrait,
    ImmutableTrait,
    GenericBoundTrait,
    MergeTraitBehaviour,
    Traits,
)

T = TypeVar("T", bound="BaseType")


# Primitive types
@dataclass(kw_only=True)
class _TraitMixin:
    traits: Traits = field(default_factory=Traits)
    compatible_traits: ClassVar[set[type[BaseTrait]]] = {ImmutableTrait}

    def base_traits(self) -> set[BaseTrait]:
        raise NotImplementedError

    def check_incompatible_traits(self) -> NoReturn | None:
        for trait in self.traits.items.values():
            if not isinstance(trait, tuple(self.compatible_traits)):
                raise SimileTraitError(f"Cannot apply trait {trait} to type {self.__class__.__name__}: incompatible trait")
        return None

    def _is_eq_traits(self, other: _TraitMixin) -> bool:
        """Check whether the type would be equal when considering traits."""
        return self.traits == other.traits

    @typing_rule("Type Refinement")
    def _is_sub_traits(self, other: _TraitMixin) -> bool:
        """Check whether the type is a sub-type when considering traits."""
        raise NotImplementedError


@dataclass(kw_only=True)
class BaseType(_TraitMixin):
    """Base type for all Simile types."""

    # Actual type methods
    def cast(self, caster: T, traits: Traits | None = None) -> T:
        """Cast the type to a different type."""
        caster = deepcopy(caster)
        # TODO only add traits if the traits make sense to add (ex. no min trait allowed on a StringType)
        # Each type should specify which traits are allowed

        if traits is not None:
            caster.traits = caster.traits.merge_copy(traits, MergeTraitBehaviour.PREFER_RIGHT)
        return caster

    def equals(self, other: BaseType) -> BoolType:
        """Operation on AST types (corresponding to ast_.Equal), not a helper for computing base types"""
        # TODO refine this if the types are not equal (then the values are probably not equal)
        return BoolType()

    def not_equals(self, other: BaseType) -> BoolType:
        return BoolType()

    # Helper methods
    def is_eq_type(self, other: BaseType, check_traits: bool = False) -> bool:

        if check_traits:
            return self._is_eq_type(other) and self._is_eq_traits(other)
        return self._is_eq_type(other)

    def _is_eq_type(self, other: BaseType) -> bool:
        raise NotImplementedError

    @typing_rule("Reflexive Subtype", "Transitive Subtype", "Sub Top Type")
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
            generic_trait = other.traits.find(GenericBoundTrait)
            if generic_trait is None:
                return is_sub_trait  # unbound generic is supertype of all types

            for other_bound in generic_trait.bound_types:
                if self.is_subtype(other_bound):
                    return is_sub_trait
            return False

        return is_sub_trait and self._is_subtype(other)

    def _is_subtype(self, other: BaseType) -> bool:
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


@dataclass
class BoolType(BaseType):
    compatible_traits: ClassVar[set[Type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        DomainTrait,
    }

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

    def base_traits(self) -> set[BaseTrait]:
        return {DomainTrait({True, False})}
