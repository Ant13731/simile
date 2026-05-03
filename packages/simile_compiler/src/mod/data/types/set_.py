from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable, TypeVar, Type, ClassVar

from src.mod.data.ast_.operators import (
    CollectionOperator,
    RelationOperator,
    BinaryOperator,
    UnaryOperator,
)
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
from src.mod.data.types.primitive import NoneType_, IntType, StringType
from src.mod.data.types.tuple_ import PairType
from src.mod.data.types.meta import AnyType_
from src.mod.data.types.composite import ProcedureType

# TODO we basically need a SetSimulator that will return the expected type, element type, and traits when executing a set operation
# Then we need a code generator that will follow through on the simulator's typed promise - maybe make a mirror class that outputs generated code instead of types?
# Whats the cleanest way to do this?
#
# At codegen time, we would like to basically cast this set type into a concrete implementation

T = TypeVar("T", bound="SetType")
V = TypeVar("V", bound="BaseType")


@dataclass
class SetType(BaseType):
    """Representation of the Simile Set type.
    This class contains the interface of sets, but can be expanded."""

    # We opt not for generic types since we dont want to hijack python's type system - we want to make our own
    element_type: BaseType
    """The Simile-type of elements in the set"""

    valid_traits: ClassVar[set[Type[Trait]]] = {
        *BaseType.valid_traits,
        OrderableTrait,
        IterableTrait,
        LiteralTrait,
        DomainTrait,
        MinTrait,
        MaxTrait,
        SizeTrait,
        ImmutableTrait,
        EmptyTrait,
        TotalTrait,
        UniqueElementsTrait,
    }

    # These functions control the return types and trait-trait interactions (where applicable)
    # I suppose this kind-of simulates the program execution just looking at traits and element types

    # Type checking methods
    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, SetType):
            return False
        return self.element_type.is_eq_type(other.element_type)

    def _is_subtype(self, other: BaseType) -> bool:
        if not isinstance(other, SetType):
            return False
        return self.element_type.is_subtype(other.element_type)

    def _is_sub_traits(self, other: BaseType) -> bool:
        if self.trait_collection.empty_trait is not None:
            return True
        raise NotImplementedError

    def _populate_mandatory_traits(self) -> None:
        self.trait_collection.iterable_trait = IterableTrait()
        self.trait_collection.unique_elements_trait = UniqueElementsTrait()

    # Programming-oriented operations
    def copy(self) -> SetType:
        """Create a copy of the set."""
        return deepcopy(self)

    def clear(self) -> NoneType_:
        """Remove all elements from the set."""
        return NoneType_()

    def is_empty(self) -> BoolType:
        """Check if the set has no elements."""
        return BoolType()

    # Atomic operations
    def add(self, element: BaseType) -> NoneType_:
        """Add an element to the set."""
        self._is_subtype_or_error(element, (self.element_type,))
        return NoneType_()

    def remove(self, element: BaseType) -> NoneType_:
        """Remove an element from the set."""
        self._is_subtype_or_error(element, (self.element_type,))
        return NoneType_()

    def in_(self, element: BaseType) -> BoolType:
        """Check if an element is in the set (membership test)."""
        self._is_subtype_or_error(element, (self.element_type,))
        return BoolType()

    def not_in(self, element: BaseType) -> BoolType:
        """Check if an element is in the set (membership test)."""
        self._is_subtype_or_error(element, (self.element_type,))
        return self.in_(element).not_()

    @classmethod
    def enumeration(cls: Type[T], element_types: list[BaseType]) -> T:
        """Create a set from an enumeration of elements of a specific type."""
        trait_collection = TraitCollection(
            size_trait=SizeTrait(size=len(element_types)),
        )
        if element_types == []:
            return cls(element_type=AnyType_(), trait_collection=trait_collection)

        return cls(element_type=BaseType.max_type(element_types), trait_collection=trait_collection)

    # Single operations
    def cardinality(self) -> IntType:
        """Return the number of elements in the set."""
        return IntType()

    def powerset(self) -> SetType:
        """Return the powerset of the set."""
        return SetType(element_type=self)

    def map(self, func: ProcedureType) -> SetType:
        """Apply a function to each element in the set."""
        if len(func.arg_types) != 1:
            raise SimileTypeError(f"Function passed to Set.map must take exactly one argument, got {len(func.arg_types)}")

        func_arg_type = next(iter(func.arg_types.values()))
        self._is_subtype_or_error(self.element_type, (func_arg_type,))

        return SetType(element_type=func.return_type)

    def choice(self) -> BaseType:
        """Select an arbitrary element from the set."""
        if self.trait_collection.empty_trait is not None:
            raise SimileTypeError("Cannot choose an element from a known empty set (EmptyTrait found).")

        return self.element_type

    def sum(self) -> BaseType:
        """Return the sum of all elements in the set."""
        return self.element_type

    def product(self) -> BaseType:
        """Return the product of all elements in the set."""
        return self.element_type

    def min(self) -> BaseType:
        """Return the minimum element in the set."""
        if self.element_type.trait_collection.orderable_trait is None:
            raise SimileTypeError(f"Cannot get minimum of set with non-orderable element type: {self.element_type}")

        return self.element_type

    def max(self) -> BaseType:
        """Return the maximum element in the set."""
        if self.element_type.trait_collection.orderable_trait is None:
            raise SimileTypeError(f"Cannot get maximum of set with non-orderable element type: {self.element_type}")

        return self.element_type

    def map_min(self, func: ProcedureType) -> BaseType:
        """Apply a weighting function to each element and return the minimum."""
        if len(func.arg_types) != 1:
            raise SimileTypeError(f"Function passed to Set.map must take exactly one argument, got {len(func.arg_types)}")

        func_arg_type = next(iter(func.arg_types.values()))
        self._is_subtype_or_error(self.element_type, (func_arg_type,))
        return self.element_type

    def map_max(self, func: ProcedureType) -> BaseType:
        """Apply a weighting function to each element and return the maximum."""
        if len(func.arg_types) != 1:
            raise SimileTypeError(f"Function passed to Set.map must take exactly one argument, got {len(func.arg_types)}")

        func_arg_type = next(iter(func.arg_types.values()))
        self._is_subtype_or_error(self.element_type, (func_arg_type,))
        return self.element_type

    # Binary operations
    def union(self, other: SetType) -> SetType:
        """Return the union of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def intersection(self, other: SetType) -> SetType:
        """Return the intersection of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def difference(self, other: SetType) -> SetType:
        """Return the difference of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def symmetric_difference(self, other: SetType) -> SetType:
        """Return the symmetric difference of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def cartesian_product(self, other: SetType) -> RelationType:
        """Return the cartesian product of this set and another set."""
        return RelationType(
            left=self.element_type,
            right=other.element_type,
        )

    def is_disjoint(self, other: SetType) -> BoolType:
        """Check if this set and another set are disjoint."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_subset(self, other: SetType) -> BoolType:
        """Check if this set is a subset of another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_subset_equals(self, other: SetType) -> BoolType:
        self._is_subtype_or_error(other, (SetType(AnyType_()),))
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_superset(self, other: SetType) -> BoolType:
        """Check if this set is a superset of another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_()),))
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_superset_equals(self, other: SetType) -> BoolType:
        self._is_subtype_or_error(other, (SetType(AnyType_()),))
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def not_is_subset(self, other: SetType) -> BoolType:
        return self.is_subset(other).not_()

    def not_is_subset_equals(self, other: SetType) -> BoolType:
        return self.is_subset_equals(other).not_()

    def not_is_superset(self, other: SetType) -> BoolType:
        return self.is_superset(other).not_()

    def not_is_superset_equals(self, other: SetType) -> BoolType:
        return self.is_superset_equals(other).not_()

    # TODO N-ary operations


@dataclass
class RelationType(SetType):
    valid_traits: ClassVar[set[Type[Trait]]] = {
        *BaseType.valid_traits,
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
    }

    def __init__(self, left: BaseType, right: BaseType, *, trait_collection: TraitCollection | None = None) -> None:
        if trait_collection is None:
            trait_collection = TraitCollection()
        super().__init__(element_type=PairType(left=left, right=right), trait_collection=trait_collection)

    @property
    def left(self) -> BaseType:
        assert isinstance(self.element_type, PairType)
        return self.element_type.left

    @property
    def right(self) -> BaseType:
        assert isinstance(self.element_type, PairType)
        return self.element_type.right

    # Tuple represents (total on domain, total on range, one-to-many, many-to-one)
    __relation_operator_table = {
        RelationOperator.RELATION: (False, False, False, False),
        RelationOperator.PARTIAL_FUNCTION: (False, False, True, False),
        RelationOperator.PARTIAL_INJECTION: (False, False, True, True),
        RelationOperator.SURJECTIVE_RELATION: (False, True, False, False),
        RelationOperator.PARTIAL_SURJECTION: (False, True, True, False),
        RelationOperator.TOTAL_RELATION: (True, False, False, False),
        RelationOperator.TOTAL_FUNCTION: (True, False, True, False),
        RelationOperator.TOTAL_INJECTION: (True, False, True, True),
        RelationOperator.TOTAL_SURJECTIVE_RELATION: (True, True, False, False),
        RelationOperator.TOTAL_SURJECTION: (True, True, True, False),
        RelationOperator.BIJECTION: (True, True, True, True),
    }

    def apply_traits_from_relation_operator(self, relation_operator: RelationOperator) -> None:
        self._add_relation_traits_from_tuple(self.__relation_operator_table[relation_operator])

    def _add_relation_traits_from_tuple(self, traits_tuple: tuple[bool, bool, bool, bool]) -> None:
        if traits_tuple[0]:
            self.trait_collection.total_on_domain_trait = TotalOnDomainTrait()
        if traits_tuple[1]:
            self.trait_collection.total_on_range_trait = TotalOnRangeTrait()
        if traits_tuple[2]:
            self.trait_collection.one_to_many_trait = OneToManyTrait()
        if traits_tuple[3]:
            self.trait_collection.many_to_one_trait = ManyToOneTrait()

    def _relation_traits_to_tuple(self) -> tuple[bool, bool, bool, bool]:
        return (
            self.trait_collection.total_on_domain_trait is not None,
            self.trait_collection.total_on_range_trait is not None,
            self.trait_collection.one_to_many_trait is not None,
            self.trait_collection.many_to_one_trait is not None,
        )

    def inverse(self) -> RelationType:
        new_type = deepcopy(self)
        relation_traits_tuple = self._relation_traits_to_tuple()
        new_relation_traits_tuple = (
            relation_traits_tuple[1],
            relation_traits_tuple[0],
            relation_traits_tuple[3],
            relation_traits_tuple[2],
        )
        new_type._add_relation_traits_from_tuple(new_relation_traits_tuple)

        return new_type

    def composition(self, other: RelationType) -> RelationType:
        try:
            BaseType.max_type([self.right, other.left])
        except SimileTypeError as e:
            raise SimileTypeError(f"Cannot compose relations with incompatible (middle) types: {self.right} and {other.left}") from e

        new_type = RelationType(left=self.left, right=other.right, trait_collection=deepcopy(self.trait_collection))
        self_relation_traits_tuple = self._relation_traits_to_tuple()
        other_relation_traits_tuple = other._relation_traits_to_tuple()
        new_relation_traits_tuple = (
            self_relation_traits_tuple[0],
            self_relation_traits_tuple[1] and other_relation_traits_tuple[1],
            self_relation_traits_tuple[2] and other_relation_traits_tuple[2],
            self_relation_traits_tuple[3] and other_relation_traits_tuple[3],
        )
        new_type._add_relation_traits_from_tuple(new_relation_traits_tuple)
        return new_type

    def function_call(self, argument: BaseType) -> BaseType:
        return self.image(argument).choice()

    def image(self, argument: BaseType) -> SetType:
        self._is_subtype_or_error(argument, (self.left,))
        # TODO transfer empty trait
        return SetType(element_type=self.right)

    def overriding(self, other: RelationType) -> RelationType:
        max_left_type = BaseType.max_type([self.left, other.left])
        max_right_type = BaseType.max_type([self.right, other.right])
        possible_types: list[BaseType] = [
            self,
            other,
            RelationType(max_left_type, max_right_type),
            BagType(max_left_type),
            SequenceType(max_right_type),
        ]
        max_type = BaseType.min_type(possible_types)
        if not isinstance(max_type, RelationType):
            raise SimileTypeError(f"Cannot override relations with incompatible types: {self} and {other} (widest type is not a relation)")
        # TODO copy traits - this is a new type after all

        new_type = deepcopy(max_type)
        self_relation_traits_tuple = self._relation_traits_to_tuple()
        other_relation_traits_tuple = other._relation_traits_to_tuple()
        new_relation_traits_tuple = (
            other_relation_traits_tuple[0],
            other_relation_traits_tuple[1],
            self_relation_traits_tuple[2] and other_relation_traits_tuple[2],
            self_relation_traits_tuple[3] and other_relation_traits_tuple[3],
        )
        new_type._add_relation_traits_from_tuple(new_relation_traits_tuple)
        return new_type

    def domain(self) -> SetType:
        return SetType(element_type=self.left)

    def range_(self) -> SetType:
        return SetType(element_type=self.right)

    def domain_restriction(self, domain_set: SetType) -> RelationType:
        self._is_subtype_or_error(domain_set, (self.domain(),))

        new_type = deepcopy(self)
        new_type.trait_collection.total_on_domain_trait = None
        return new_type

    def domain_subtraction(self, domain_set: SetType) -> RelationType:
        self._is_subtype_or_error(domain_set, (self.domain(),))

        new_type = deepcopy(self)
        new_type.trait_collection.total_on_domain_trait = None
        return new_type

    def range_restriction(self, range_set: SetType) -> RelationType:
        self._is_subtype_or_error(range_set, (self.range_(),))

        new_type = deepcopy(self)
        new_type.trait_collection.total_on_range_trait = None
        return new_type

    def range_subtraction(self, range_set: SetType) -> RelationType:
        self._is_subtype_or_error(range_set, (self.range_(),))

        new_type = deepcopy(self)
        new_type.trait_collection.total_on_range_trait = None
        return new_type

    def bag_image(self, bag: BagType) -> BagType:
        # Get traits from here. This also needs to be run to check for type errors from dependent operations
        self.inverse().composition(bag)

        return BagType(element_type=self.right)


@dataclass
class BagType(RelationType):

    def __init__(self, element_type: BaseType, *, trait_collection: TraitCollection | None = None) -> None:
        super().__init__(left=element_type, right=IntType(), trait_collection=trait_collection)
        self.trait_collection.many_to_one_trait = ManyToOneTrait()

    @property
    def element_type_(self) -> BaseType:
        return self.left

    def _populate_mandatory_traits(self) -> None:
        super()._populate_mandatory_traits()
        self.trait_collection.many_to_one_trait = ManyToOneTrait()

    def bag_union(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, (BagType(AnyType_()),))
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def bag_intersection(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, (BagType(AnyType_()),))
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def bag_add(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, (BagType(AnyType_()),))
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def bag_difference(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, (BagType(AnyType_()),))
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def size(self) -> IntType:
        """Return the total number of elements in the bag, counting multiplicities."""
        return IntType()


@dataclass
class SequenceType(RelationType):

    def __init__(self, element_type: BaseType, *, trait_collection: TraitCollection | None = None) -> None:
        super().__init__(left=IntType(), right=element_type, trait_collection=trait_collection)
        self.trait_collection.many_to_one_trait = ManyToOneTrait()

    @property
    def element_type_(self) -> BaseType:
        return self.right

    def _populate_mandatory_traits(self) -> None:
        super()._populate_mandatory_traits()
        self.trait_collection.many_to_one_trait = ManyToOneTrait()

    def concat(self, other: SequenceType) -> SequenceType:
        self._is_subtype_or_error(other, (SequenceType(AnyType_()),))
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return SequenceType(element_type=new_element_type)


@dataclass
class EnumType(SetType):
    # Internally a set of identifiers
    # element_type = StringType()  # TODO add trait domain
    members: set[str] = field(default_factory=set)

    def __post_init__(self):
        self.element_type = StringType()
        super().__post_init__()

    def _populate_mandatory_traits(self) -> None:
        from src.mod.data.ast_ import String

        super()._populate_mandatory_traits()
        self.trait_collection.immutable_trait = ImmutableTrait()
        self.trait_collection.domain_trait = DomainTrait([String(member) for member in self.members])
        self.trait_collection.size_trait = SizeTrait(len(self.members))

        self.element_type.trait_collection.immutable_trait = ImmutableTrait()
