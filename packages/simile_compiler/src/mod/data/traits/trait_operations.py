from enum import Enum, auto
from dataclasses import dataclass, field
from typing import TypeVar


from src.mod.data.traits.base import (
    SimileLiteralAsPythonOrderable,
    SimileLiteralAsPython,
    BaseTrait,
    ImmutableTrait,
    LiteralTrait,
    UndefinedTrait,
    GenericBoundTrait,
)
from src.mod.data.traits.error import SimileTraitError
from src.mod.data.traits.orderable import (
    OrderableTrait,
    MinTrait,
    MaxTrait,
)
from src.mod.data.traits.procedure import (
    TreatAsExprTrait,
)
from src.mod.data.traits.relation import (
    OneToManyTrait,
    ManyToOneTrait,
    TotalOnDomainTrait,
    TotalOnRangeTrait,
)
from src.mod.data.traits.set_ import (
    DomainTrait,
    IterableTrait,
    UniqueTrait,
    EmptyTrait,
    SizeTrait,
    TotalTrait,
)


class MergeTraitBehaviour(Enum):
    PREFER_LEFT = auto()
    PREFER_RIGHT = auto()
    THROW_ON_UNRESOLVABLE = auto()


T = TypeVar("T", bound=BaseTrait)


@dataclass
class Traits:
    items: dict[type[BaseTrait], BaseTrait] = field(default_factory=dict)

    def __init__(self, traits: set[BaseTrait] | None = None):
        self.items = {}
        if traits is not None:
            for trait in traits:
                self.add(trait)

    def find(self, trait_type: type[T]) -> T | None:
        return self.items.get(trait_type)  # type: ignore

    def add(self, item: BaseTrait) -> None:
        if type(item) not in self.items:
            self.items[type(item)] = item
            return
        if type(item) == GenericBoundTrait:
            existing_generic_bound_trait = self.find(GenericBoundTrait)
            assert existing_generic_bound_trait is not None
            combined_bound_trait = existing_generic_bound_trait.merge_copy(item)
            self.items[GenericBoundTrait] = combined_bound_trait
            return
        raise SimileTraitError(f"Trait of type {type(item)} already exists in the collection.")

    def remove(self, item: BaseTrait) -> None:
        if type(item) in self.items and self.items[type(item)] == item:
            del self.items[type(item)]

    def update(self, other: set[BaseTrait]) -> None:
        for trait in other:
            self.add(trait)

    def deduplicate(self) -> None:
        # Rules (TODO verify with spec):
        # - DomainTrait with no values => Remove DomainTrait
        raise NotImplementedError

    def derive(self) -> None:
        # Rules (TODO verify with spec):
        # - DomainTrait + Orderable => MinTrait and MaxTrait
        # - DomainTrait + Orderable + Min/MaxTrait where domain has a value smaller/larger => widened Min/MaxTrait
        # - Literal + no DomainTrait => DomainTrait with one literal value
        # - Literal + DomainTrait without Literal => DomainTrait with literal value added
        # - Min/MaxTrait => Orderable
        # - Unique + Size + Domain + Size==len(Domain) => Total
        # - Size == 0 => Empty
        # - Size != 0 + Empty => remove Empty
        # - Size => Iterable
        # - Literal + Orderable + no Min/Max => Min/Max with literal value
        # TODO write down trait-trait dependencies
        raise NotImplementedError

    def check_compatible(self) -> None:
        # Check if specific traits are incompatible with one another (ex. max below min)
        raise NotImplementedError

    def merge_copy(self, other: Traits, behaviour: MergeTraitBehaviour = MergeTraitBehaviour.PREFER_LEFT) -> Traits:
        # Merging traits generally takes the widest possible value (union of the underlying sets)
        # But some traits may actually narrow upon merging with specific operations (ex. an intersection of two sets with different domains)
        # So we need to carefully evaluate what needs narrowing and what needs widening

        # Narrowing merges:
        # - DomainTrait unions with DomainTrait
        # - MinTrait takes the min of both
        # - MaxTrait takes the max of both
        # - ...
        raise NotImplementedError


# Old merge functions, delete when done:
# def _fill_implicit_traits(self) -> None:
#     """Some traits implicitly encompass others. This fills in that closure.
#     Ex. a Literal[1] implies min=1 and max=1.

#     Mandatory traits should have been filled in first, restricted traits should be checked after
#     """

#     # Domain Empty
#     if self.domain_trait and len(self.domain_trait.values) == 0:
#         self.domain_trait = None

#     # Literal Implies a Domain
#     if self.literal_trait and self.domain_trait is None:
#         self.domain_trait = DomainTrait([self.literal_trait.value])

#     # Literal within Domain
#     if self.literal_trait and self.domain_trait:
#         if self.literal_trait.value not in self.domain_trait.values:
#             self.domain_trait = DomainTrait(self.domain_trait.values + [self.literal_trait.value])

#     # Orderable Domain without Min
#     if self.domain_trait and self.orderable_trait and self.min_trait is None:
#         self.min_trait = MinTrait.from_domain_trait(self.domain_trait)

#     # Orderable Domain with Min
#     if self.domain_trait and self.orderable_trait and self.min_trait:
#         min_trait_from_domain = MinTrait.from_domain_trait(self.domain_trait)
#         if min_trait_from_domain:
#             self.min_trait = self.min_trait.merge(min_trait_from_domain)

#     # Orderable Domain without Max
#     if self.domain_trait and self.orderable_trait and self.max_trait is None:
#         self.max_trait = MaxTrait.from_domain_trait(self.domain_trait)

#     # Orderable Domain with Max
#     if self.domain_trait and self.orderable_trait and self.max_trait:
#         max_trait_from_domain = MaxTrait.from_domain_trait(self.domain_trait)
#         if max_trait_from_domain:
#             self.max_trait = self.max_trait.merge(max_trait_from_domain)

#     # Min implies Order
#     if self.min_trait and self.orderable_trait is None:
#         self.orderable_trait = OrderableTrait()

#     # Max implies Order
#     if self.max_trait and self.orderable_trait is None:
#         self.orderable_trait = OrderableTrait()

#     # Full set
#     if self.unique_elements_trait and self.size_trait and self.domain_trait and self.size_trait.size == len(self.domain_trait.values) and self.empty_trait is None:
#         self.total_trait = TotalTrait()

#     # Empty Size
#     if self.size_trait and self.size_trait.size == 0:
#         self.empty_trait = EmptyTrait()

#     # Non-empty Size
#     if self.size_trait and self.size_trait.size > 0:
#         self.empty_trait = None

#     # Size implies Iterable
#     if self.size_trait:
#         self.iterable_trait = IterableTrait()

#     # Orderable Literal is Min
#     if self.literal_trait and self.orderable_trait and self.min_trait is None:
#         self.min_trait = MinTrait(value=self.literal_trait.value)

#     # Orderable Literal is Max
#     if self.literal_trait and self.orderable_trait and self.max_trait is None:
#         self.max_trait = MaxTrait(value=self.literal_trait.value)

# def merge(self, other: TraitCollection, prioritize_self_over_other: bool = False) -> TraitCollection:
#     """Merge this TraitCollection with another, returning a new TraitCollection.

#     Prioritize_self_over_other indicates whether to keep self's traits when both are present."""
#     merged = deepcopy(self)

#     for trait in fields(merged):
#         self_trait = getattr(merged, trait.name)
#         other_trait = getattr(other, trait.name)

#         if self_trait is None:
#             continue
#         if other_trait is None or prioritize_self_over_other:
#             setattr(merged, trait.name, self_trait)
#             continue

#         if hasattr(self_trait, "merge"):
#             merged_trait = self_trait.merge(other_trait)
#             setattr(merged, trait.name, merged_trait)

#     merged._fill_implicit_traits()
#     return merged
