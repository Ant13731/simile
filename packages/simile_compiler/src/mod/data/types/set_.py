from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, TypeVar, ClassVar

from src.mod.data.ast_.operators import (
    CollectionOperator,
    RelationOperator,
    BinaryOperator,
    UnaryOperator,
)
from src.mod.data.types.error import SimileTypeError
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
    RelationalDomainTrait,
    RelationalRangeTrait,
    Traits,
)
from src.mod.data.types.base import BaseType, BoolType, _TraitMixin
from src.mod.data.types.primitive import FloatType, NoneType_, IntType, StringType
from src.mod.data.types.tuple_ import PairType
from src.mod.data.types.meta import AnyType_
from src.mod.data.types.typing_rule_decorator import typing_rule

if TYPE_CHECKING:
    from src.mod.data.types.composite import ProcedureType
    from src.mod.data.symbol_table.entry import SymbolTableIdentifierEntry

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

    compatible_traits: ClassVar[set[type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        DomainTrait,
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
        UniqueTrait,
    }

    # These functions control the return types and trait-trait interactions (where applicable)
    # I suppose this kind-of simulates the program execution just looking at traits and element types

    # Type checking methods
    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, SetType):
            return False
        return self.element_type.is_eq_type(other.element_type)

    @typing_rule("Sub Set")
    def _is_subtype(self, other: BaseType) -> bool:
        if not isinstance(other, SetType):
            return False
        return self.element_type.is_subtype(other.element_type)

    def _is_sub_traits(self, other: _TraitMixin) -> bool:
        empty_traits = self.traits.find(EmptyTrait)
        if empty_traits is not None:
            return True
        raise NotImplementedError

    def base_traits(self) -> set[BaseTrait]:
        return {IterableTrait(), UniqueTrait()}

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
    def enumeration(cls, element_types: list[BaseType]) -> SetType:
        """Create a set from an enumeration of elements of a specific type."""
        traits: set[BaseTrait] = {SizeTrait(size=len(element_types))}
        if element_types == []:
            return cls.set_constructor(element_type=AnyType_(), traits=traits)

        return cls.set_constructor(element_type=BaseType.max_type(element_types), traits=traits)

    @classmethod
    def set_constructor(cls, element_type: BaseType, traits: set[BaseTrait]) -> SetType:
        return cls(element_type=element_type, traits=Traits(traits))

    # Single operations
    def cardinality(self) -> IntType:
        """Return the number of elements in the set."""
        return IntType()

    @classmethod
    def powerset(cls, element_type: BaseType) -> SetType:
        """Return the powerset of the set."""
        return SetType(element_type=element_type)

    def map(self, func: ProcedureType) -> SetType:
        """Apply a function to each element in the set."""
        if len(func.arg_types.items) != 1:
            raise SimileTypeError(f"Function passed to Set.map must take exactly one argument, got {len(func.arg_types.items)}")

        func_arg_type = next(iter(func.arg_types.items))
        self._is_subtype_or_error(self.element_type, (func_arg_type,))

        return SetType(element_type=func.return_type)

    def choice(self) -> BaseType:
        """Select an arbitrary element from the set."""
        if self.traits.find(EmptyTrait) is not None:
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
        if self.traits.find(OrderableTrait) is None:
            raise SimileTypeError(f"Cannot get minimum of set with non-orderable element type: {self.element_type}")

        return self.element_type

    def max(self) -> BaseType:
        """Return the maximum element in the set."""
        if self.traits.find(OrderableTrait) is None:
            raise SimileTypeError(f"Cannot get maximum of set with non-orderable element type: {self.element_type}")

        return self.element_type

    def map_min(self, func: ProcedureType) -> BaseType:
        """Apply a weighting function to each element and return the minimum."""
        if len(func.arg_types.items) != 1:
            raise SimileTypeError(f"Function passed to Set.map must take exactly one argument, got {len(func.arg_types.items)}")

        # TODO check that func actually resolves to an int/orderable?
        func_arg_type = next(iter(func.arg_types.items))
        self._is_subtype_or_error(self.element_type, (func_arg_type,))
        return self.element_type

    def map_max(self, func: ProcedureType) -> BaseType:
        """Apply a weighting function to each element and return the maximum."""
        if len(func.arg_types.items) != 1:
            raise SimileTypeError(f"Function passed to Set.map must take exactly one argument, got {len(func.arg_types.items)}")

        func_arg_type = next(iter(func.arg_types.items))
        self._is_subtype_or_error(self.element_type, (func_arg_type,))
        return self.element_type

    # Binary operations
    def union(self, other: BaseType) -> SetType:
        """Return the union of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def intersection(self, other: BaseType) -> SetType:
        """Return the intersection of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def difference(self, other: BaseType) -> SetType:
        """Return the difference of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def symmetric_difference(self, other: BaseType) -> SetType:
        """Return the symmetric difference of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)

        new_element_type = BaseType.max_type([self.element_type, other.element_type])
        return SetType(element_type=new_element_type)

    def cartesian_product(self, other: BaseType) -> RelationType:
        """Return the cartesian product of this set and another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)
        return RelationType(
            left=self.element_type,
            right=other.element_type,
        )

    def is_disjoint(self, other: BaseType) -> BoolType:
        """Check if this set and another set are disjoint."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_subset(self, other: BaseType) -> BoolType:
        """Check if this set is a subset of another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_subset_equals(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, SetType(AnyType_()))
        assert isinstance(other, SetType)
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_superset(self, other: BaseType) -> BoolType:
        """Check if this set is a superset of another set."""
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def is_superset_equals(self, other: BaseType) -> BoolType:
        self._is_subtype_or_error(other, (SetType(AnyType_())))
        assert isinstance(other, SetType)
        # Check that element types are compatible but throw away the result
        BaseType.max_type([self.element_type, other.element_type])
        return BoolType()

    def not_is_subset(self, other: BaseType) -> BoolType:
        return self.is_subset(other).not_()

    def not_is_subset_equals(self, other: BaseType) -> BoolType:
        return self.is_subset_equals(other).not_()

    def not_is_superset(self, other: BaseType) -> BoolType:
        return self.is_superset(other).not_()

    def not_is_superset_equals(self, other: BaseType) -> BoolType:
        return self.is_superset_equals(other).not_()


@dataclass
class RelationType(SetType):
    compatible_traits: ClassVar[set[type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        OrderableTrait,
        IterableTrait,
        MinTrait,
        MaxTrait,
        SizeTrait,
        ImmutableTrait,
        TotalOnDomainTrait,
        TotalOnRangeTrait,
        RelationalDomainTrait,
        RelationalRangeTrait,
        ManyToOneTrait,
        OneToManyTrait,
        EmptyTrait,
        TotalTrait,
        UniqueTrait,
    }

    def __init__(self, left: BaseType, right: BaseType, *, traits: Traits | None = None) -> None:
        if traits is None:
            traits = Traits()
        super().__init__(element_type=PairType(left=left, right=right), traits=traits)

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

    def _add_relation_traits_from_tuple(self, traits_tuple: tuple[bool, bool, bool, bool]) -> set[BaseTrait]:
        traits: set[BaseTrait] = set()
        if traits_tuple[0]:
            traits.add(TotalOnDomainTrait())
        if traits_tuple[1]:
            traits.add(TotalOnRangeTrait())
        if traits_tuple[2]:
            traits.add(OneToManyTrait())
        if traits_tuple[3]:
            traits.add(ManyToOneTrait())
        return traits

    def _relation_traits_to_tuple(self) -> tuple[bool, bool, bool, bool]:
        total_on_domain_trait = self.traits.find(TotalOnDomainTrait)
        total_on_range_trait = self.traits.find(TotalOnRangeTrait)
        one_to_many_trait = self.traits.find(OneToManyTrait)
        many_to_one_trait = self.traits.find(ManyToOneTrait)
        return (
            total_on_domain_trait is not None,
            total_on_range_trait is not None,
            one_to_many_trait is not None,
            many_to_one_trait is not None,
        )

    @classmethod
    def set_constructor(cls, element_type: BaseType, traits: set[BaseTrait]) -> RelationType:
        """Cast a SetType to a RelationType, if possible."""
        if not isinstance(element_type, PairType):
            raise SimileTypeError(f"Cannot cast SetType with non-PairType element type {element_type} to RelationType")
        return RelationType(left=element_type.left, right=element_type.right, traits=Traits(traits))

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

    def composition(self, other: BaseType) -> RelationType:
        self._is_subtype_or_error(other, RelationType(AnyType_(), AnyType_()))
        assert isinstance(other, RelationType)

        try:
            BaseType.max_type([self.right, other.left])
        except SimileTypeError as e:
            raise SimileTypeError(f"Cannot compose relations with incompatible (middle) types: {self.right} and {other.left}") from e

        new_type = RelationType(left=self.left, right=other.right, traits=deepcopy(self.traits))
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

    def overriding(self, other: BaseType) -> RelationType:
        self._is_subtype_or_error(other, RelationType(AnyType_(), AnyType_()))
        assert isinstance(other, RelationType)

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

    def domain_restriction(self, domain_set: BaseType) -> RelationType:
        self._is_subtype_or_error(domain_set, (self.domain(),))
        assert isinstance(domain_set, SetType)

        new_type = deepcopy(self)
        try:
            new_type.traits.remove(TotalOnDomainTrait())
        except KeyError:
            pass
        return new_type

    def domain_subtraction(self, domain_set: BaseType) -> RelationType:
        self._is_subtype_or_error(domain_set, (self.domain(),))
        assert isinstance(domain_set, SetType)

        new_type = deepcopy(self)
        new_type.traits.remove(TotalOnDomainTrait())
        return new_type

    def range_restriction(self, range_set: BaseType) -> RelationType:
        self._is_subtype_or_error(range_set, (self.range_(),))
        assert isinstance(range_set, SetType)

        new_type = deepcopy(self)
        new_type.traits.remove(TotalOnRangeTrait())
        return new_type

    def range_subtraction(self, range_set: BaseType) -> RelationType:
        self._is_subtype_or_error(range_set, (self.range_(),))
        assert isinstance(range_set, SetType)

        new_type = deepcopy(self)
        new_type.traits.remove(TotalOnRangeTrait())
        return new_type

    def bag_image(self, bag: BagType) -> BagType:
        # Get traits from here. This also needs to be run to check for type errors from dependent operations
        self.inverse().composition(bag)

        return BagType(element_type=self.right)


@dataclass
class BagType(RelationType):

    def __init__(self, element_type: BaseType, *, traits: Traits | None = None) -> None:
        super().__init__(left=element_type, right=IntType(), traits=traits)

    @property
    def element_type_(self) -> BaseType:
        return self.left

    @classmethod
    def set_constructor(cls, element_type: BaseType, traits: set[BaseTrait]) -> BagType:
        return cls(element_type=element_type, traits=Traits(traits))

    def base_traits(self) -> set[BaseTrait]:
        return {ManyToOneTrait()}

    def bag_union(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, BagType(AnyType_()))
        assert isinstance(other, BagType)
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def bag_intersection(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, BagType(AnyType_()))
        assert isinstance(other, BagType)
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def bag_add(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, BagType(AnyType_()))
        assert isinstance(other, BagType)
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def bag_difference(self, other: BagType) -> BagType:
        self._is_subtype_or_error(other, BagType(AnyType_()))
        assert isinstance(other, BagType)
        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return BagType(element_type=new_element_type)

    def size(self) -> IntType:
        """Return the total number of elements in the bag, counting multiplicities."""
        return IntType()


@dataclass
class SequenceType(RelationType):

    def __init__(self, element_type: BaseType, *, traits: Traits | None = None) -> None:
        super().__init__(left=IntType(), right=element_type, traits=traits)

    @classmethod
    def set_constructor(cls, element_type: BaseType, traits: set[BaseTrait]) -> SequenceType:
        return cls(element_type=element_type, traits=Traits(traits))

    @property
    def element_type_(self) -> BaseType:
        return self.right

    def base_traits(self) -> set[BaseTrait]:
        return {ManyToOneTrait()}

    def concat(self, other: BaseType) -> SequenceType:
        self._is_subtype_or_error(other, SequenceType(AnyType_()))
        assert isinstance(other, SequenceType)

        new_element_type = BaseType.max_type([self.element_type_, other.element_type_])
        return SequenceType(element_type=new_element_type)


@dataclass
class EnumType(SetType):
    # Internally a set of identifiers
    element_type: BaseType = field(default_factory=StringType)
    members: set[str] = field(default_factory=set)

    def base_traits(self) -> set[BaseTrait]:
        return {
            ImmutableTrait(),
            DomainTrait(set(self.members)),
            SizeTrait(len(self.members)),
        }


@dataclass
class EnumItemType(BaseType):
    enum_type: EnumType


@dataclass
class QuantificationBodyIntermediary(BaseType):
    return_type: BaseType

    def forall(self) -> BoolType:
        self._is_subtype_or_error(self.return_type, BoolType())
        assert isinstance(self.return_type, BoolType)
        return self.return_type

    def exists(self) -> BoolType:
        self._is_subtype_or_error(self.return_type, BoolType())
        assert isinstance(self.return_type, BoolType)
        return self.return_type

    def union_all(self) -> SetType:
        self._is_subtype_or_error(self.return_type, SetType(AnyType_()))
        assert isinstance(self.return_type, SetType)
        return self.return_type

    def intersection_all(self) -> SetType:
        self._is_subtype_or_error(self.return_type, SetType(AnyType_()))
        assert isinstance(self.return_type, SetType)
        return self.return_type

    def set_comprehension(self) -> SetType:
        return SetType(self.return_type)

    def relation_comprehension(self) -> RelationType:
        self._is_subtype_or_error(self.return_type, PairType(AnyType_(), AnyType_()))
        assert isinstance(self.return_type, PairType)
        return RelationType(self.return_type.left, self.return_type.right)

    def bag_comprehension(self) -> BagType:
        return BagType(self.return_type)

    def sequence_comprehension(self) -> SequenceType:
        return SequenceType(self.return_type)

    def sum(self) -> IntType | FloatType:
        self._is_subtype_or_error(self.return_type, (IntType(), FloatType()))
        assert isinstance(self.return_type, IntType | FloatType)
        return self.return_type

    def product(self) -> IntType | FloatType:
        self._is_subtype_or_error(self.return_type, (IntType(), FloatType()))
        assert isinstance(self.return_type, IntType | FloatType)
        return self.return_type

    def min(self) -> BaseType:  # IntType | FloatType:
        # TODO refine subtype to consider traits (like the orderable trait)
        # self._is_subtype_or_error(self.return_type, (IntType(), FloatType()))
        # assert isinstance(self.return_type, IntType | FloatType)
        return self.return_type

    def max(self) -> BaseType:  # IntType | FloatType:
        # self._is_subtype_or_error(self.return_type, (IntType(), FloatType()))
        # assert isinstance(self.return_type, IntType | FloatType)
        return self.return_type

    def iter_(self) -> BaseType:
        return self.return_type

    def fold(self) -> BaseType:
        return self.return_type

    def base_traits(self) -> set[BaseTrait]:
        return set()


@dataclass
class GeneratorIntermediary(BaseType):
    iterator_type: BaseType

    def base_traits(self) -> set[BaseTrait]:
        return set()
