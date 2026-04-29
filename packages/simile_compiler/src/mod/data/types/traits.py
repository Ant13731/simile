from __future__ import annotations
from dataclasses import dataclass, field, fields
from copy import deepcopy
from typing import ClassVar, Any, TYPE_CHECKING

from src.mod.data.types.error import SimileTypeError


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.mod.data.ast_.base import ASTNode
    from src.mod.data.types.base import BaseType


# TODO make a function to translate ASTNodes into traits when they appear in the trait position
# Parser should parse as an astnode, then typechecker/symb table will try to promote to traits where applicable
def interpret_astnode_as_traits(node: ASTNode) -> list[Trait]:
    """Interpret an ASTNode as a Trait, if possible."""
    raise NotImplementedError


@dataclass
class TraitCollection:
    immutable_trait: ImmutableTrait | None = None

    # Intended for arithmetic use
    orderable_trait: OrderableTrait | None = None
    min_trait: MinTrait | None = None
    max_trait: MaxTrait | None = None

    # Restricting values of a type
    # @deprecated
    # literal_traits: list[LiteralTrait] = field(default_factory=list)

    literal_trait: LiteralTrait | None = None
    domain_trait: DomainTrait | None = None

    # Useful for sets/collections
    iterable_trait: IterableTrait | None = None
    empty_trait: EmptyTrait | None = None
    unique_elements_trait: UniqueElementsTrait | None = None
    size_trait: SizeTrait | None = None

    # On relations, total_trait means every possible pair is enumerated (ie. cartesian product of domain and range)
    # On sets, this just means the set contains every possible element from its domain
    total_trait: TotalTrait | None = None

    # Relation type only - no static validation available for this...
    total_on_domain_trait: TotalOnDomainTrait | None = None
    total_on_range_trait: TotalOnRangeTrait | None = None
    many_to_one_trait: ManyToOneTrait | None = None
    one_to_many_trait: OneToManyTrait | None = None

    # For generic types that may be bound to certain types
    generic_bound_trait: GenericBoundTrait | None = None

    def __post_init__(self):
        self._fill_implicit_traits()

    @property
    def one_to_one(self) -> bool:
        return self.one_to_many_trait is not None and self.many_to_one_trait is not None

    def _fill_implicit_traits(self) -> None:
        """Some traits implicitly encompass others. This fills in that closure.
        Ex. a Literal[1] implies min=1 and max=1.

        Mandatory traits should have been filled in first, restricted traits should be checked after
        """

        # Domain Empty
        if self.domain_trait and len(self.domain_trait.values) == 0:
            self.domain_trait = None

        # Literal Implies a Domain
        if self.literal_trait and self.domain_trait is None:
            self.domain_trait = DomainTrait([self.literal_trait.value])

        # Literal within Domain
        if self.literal_trait and self.domain_trait:
            if self.literal_trait.value not in self.domain_trait.values:
                self.domain_trait = DomainTrait(self.domain_trait.values + [self.literal_trait.value])

        # Orderable Domain without Min
        if self.domain_trait and self.orderable_trait and self.min_trait is None:
            self.min_trait = MinTrait.from_domain_trait(self.domain_trait)

        # Orderable Domain with Min
        if self.domain_trait and self.orderable_trait and self.min_trait:
            min_trait_from_domain = MinTrait.from_domain_trait(self.domain_trait)
            if min_trait_from_domain:
                self.min_trait = self.min_trait.merge(min_trait_from_domain)

        # Orderable Domain without Max
        if self.domain_trait and self.orderable_trait and self.max_trait is None:
            self.max_trait = MaxTrait.from_domain_trait(self.domain_trait)

        # Orderable Domain with Max
        if self.domain_trait and self.orderable_trait and self.max_trait:
            max_trait_from_domain = MaxTrait.from_domain_trait(self.domain_trait)
            if max_trait_from_domain:
                self.max_trait = self.max_trait.merge(max_trait_from_domain)

        # Min implies Order
        if self.min_trait and self.orderable_trait is None:
            self.orderable_trait = OrderableTrait()

        # Max implies Order
        if self.max_trait and self.orderable_trait is None:
            self.orderable_trait = OrderableTrait()

        # Full set
        if self.unique_elements_trait and self.size_trait and self.domain_trait and self.size_trait.size == len(self.domain_trait.values) and self.empty_trait is None:
            self.total_trait = TotalTrait()

        # Empty Size
        if self.size_trait and self.size_trait.size == 0:
            self.empty_trait = EmptyTrait()

        # Non-empty Size
        if self.size_trait and self.size_trait.size > 0:
            self.empty_trait = None

        # Size implies Iterable
        if self.size_trait:
            self.iterable_trait = IterableTrait()

        # Orderable Literal is Min
        if self.literal_trait and self.orderable_trait and self.min_trait is None:
            self.min_trait = MinTrait(value=self.literal_trait.value)

        # Orderable Literal is Max
        if self.literal_trait and self.orderable_trait and self.max_trait is None:
            self.max_trait = MaxTrait(value=self.literal_trait.value)

    def merge(self, other: TraitCollection, prioritize_self_over_other: bool = False) -> TraitCollection:
        """Merge this TraitCollection with another, returning a new TraitCollection.

        Prioritize_self_over_other indicates whether to keep self's traits when both are present."""
        merged = deepcopy(self)

        for trait in fields(merged):
            self_trait = getattr(merged, trait.name)
            other_trait = getattr(other, trait.name)

            if self_trait is None:
                continue
            if other_trait is None or prioritize_self_over_other:
                setattr(merged, trait.name, self_trait)
                continue

            if hasattr(self_trait, "merge"):
                merged_trait = self_trait.merge(other_trait)
                setattr(merged, trait.name, merged_trait)

        merged._fill_implicit_traits()
        return merged


@dataclass
class Trait:
    """A trait that modifies the behavior of a type (usually based on the element type or expected element values).

    Traits can be used to indicate special properties of the set, such as ordering,
    uniqueness, or other characteristics that affect how the set operates.
    """

    name: ClassVar[str]


@dataclass
class OrderableTrait(Trait):
    name: ClassVar[str] = "orderable"

    required_methods: ClassVar[set[str]] = {
        "greater_than",
        "less_than",
        "greater_than_equals",
        "less_than_equals",
    }

    @classmethod
    def is_orderable(cls, values: list[ASTNode]) -> bool:
        for value in values:
            if value.get_type.trait_collection.orderable_trait is None:  # type: ignore # TODO implement
                return False
        return True


@dataclass
class UniqueElementsTrait(Trait):
    name: ClassVar[str] = "unique_elements"


@dataclass
class IterableTrait(Trait):
    name: ClassVar[str] = "iterable"


@dataclass
class LiteralTrait(Trait):
    name: ClassVar[str] = "literal"
    value: ASTNode


@dataclass
class DomainTrait(Trait):
    name: ClassVar[str] = "domain"
    values: list[ASTNode]

    def __post_init__(self):
        # Ensure all values are unique
        unique_values = []
        for literal in self.values:
            if literal not in unique_values:
                unique_values.append(literal)
        self.values = unique_values

    def merge(self, other: DomainTrait) -> DomainTrait:
        combined_values = self.values
        for value in other.values:
            if value not in combined_values:
                combined_values.append(value)

        return self.__class__(values=combined_values)


@dataclass
class MinTrait(Trait):
    name: ClassVar[str] = "minimum"
    value: Any | ASTNode

    @classmethod
    def from_domain_trait(cls, trait: DomainTrait) -> MinTrait | None:
        if not OrderableTrait.is_orderable(trait.values):
            return None

        min_value = None
        for value in trait.values:
            # Most ASTNodes wont have literal_min defined
            # This is mostly meant for ints and floats
            if not hasattr(value, "literal_min"):
                return None

            if min_value is None:
                min_value = value
                continue

            # When literal_min returns None, that means that one of the inputs wasn't a literal
            min_candidate = value.literal_min(min_value)  # type: ignore
            if min_candidate is None:
                return None

            min_value = value

        return cls(value=min_value)

    def merge(self, other: MinTrait) -> MinTrait:
        if not hasattr(self.value, "literal_min"):
            raise SimileTypeError("Cannot merge MinTrait: values are not comparable")

        min_candidate = self.value.literal_min(other.value)  # type: ignore
        if min_candidate is None:
            raise SimileTypeError("Cannot merge MinTrait: values are not comparable")
        return MinTrait(value=min_candidate)


@dataclass
class MaxTrait(Trait):
    name: ClassVar[str] = "maximum"
    value: Any | ASTNode

    @classmethod
    def from_domain_trait(cls, trait: DomainTrait) -> MaxTrait | None:
        if not OrderableTrait.is_orderable(trait.values):
            return None

        max_value = None
        for value in trait.values:
            # Most ASTNodes wont have literal_max defined
            # This is mostly meant for ints and floats
            if not hasattr(value, "literal_max"):
                return None

            if max_value is None:
                max_value = value
                continue

            # When literal_max returns None, that means that one of the inputs wasn't a literal
            max_candidate = value.literal_max(max_value)  # type: ignore
            if max_candidate is None:
                return None

            max_value = value

        return cls(value=max_value)

    def merge(self, other: MaxTrait) -> MaxTrait:
        if not hasattr(self.value, "literal_max"):
            raise SimileTypeError("Cannot merge MaxTrait: values are not comparable")

        max_candidate = self.value.literal_max(other.value)  # type: ignore
        if max_candidate is None:
            raise SimileTypeError("Cannot merge MaxTrait: values are not comparable")
        return MaxTrait(value=max_candidate)


@dataclass
class SizeTrait(Trait):
    name: ClassVar[str] = "size"
    size: int


@dataclass
class ImmutableTrait(Trait):
    name: ClassVar[str] = "immutable"


@dataclass
class TotalTrait(Trait):
    name: ClassVar[str] = "total"


@dataclass
class EmptyTrait(Trait):
    name: ClassVar[str] = "empty"


@dataclass
class TotalOnDomainTrait(Trait):
    name: ClassVar[str] = "total_on_domain"


@dataclass
class TotalOnRangeTrait(Trait):
    name: ClassVar[str] = "surjective"


@dataclass
class ManyToOneTrait(Trait):
    name: ClassVar[str] = "many_to_one"


@dataclass
class OneToManyTrait(Trait):
    name: ClassVar[str] = "one_to_many"


@dataclass
class GenericBoundTrait(Trait):
    name: ClassVar[str] = "generic_bound"
    bound_types: list[BaseType]
