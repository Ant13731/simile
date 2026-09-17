from enum import Enum, auto
from dataclasses import dataclass, field
from typing import TypeVar, get_args
from copy import copy


from src.mod.data.traits.base import (
    SimileLiteralAsPythonOrderable,
    SimileLiteralAsPython,
    BaseTrait,
    ImmutableTrait,
    LiteralTrait,
    UndefinedTrait,
)
from src.mod.data.traits.meta import (
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
    # THROW_ON_UNRESOLVABLE = auto()


T = TypeVar("T", bound=BaseTrait)


@dataclass(init=False)
class InternalTraitCollection:
    items: dict[type[BaseTrait], BaseTrait] = field(default_factory=dict)

    def __init__(self, traits: set[BaseTrait] | None = None):
        super().__init__()
        self.items = {}
        if traits is not None:
            for trait in traits:
                self.add(trait)

    def find(self, trait_type: type[T]) -> T | None:
        return self.items.get(trait_type)  # type: ignore

    def add(self, item: BaseTrait, clobber_existing: bool = True) -> None:
        if type(item) == GenericBoundTrait:
            existing_generic_bound_trait = self.find(GenericBoundTrait)
            assert existing_generic_bound_trait is not None
            combined_bound_trait = existing_generic_bound_trait.merge_copy(item)
            self.items[GenericBoundTrait] = combined_bound_trait
            return
        if clobber_existing or type(item) not in self.items:
            self.items[type(item)] = item
            return
        raise SimileTraitError(f"Trait of type {type(item)} already exists in the collection.")

    def remove(self, item: BaseTrait) -> None:
        if type(item) in self.items and self.items[type(item)] == item:
            del self.items[type(item)]

    def update(self, other: set[BaseTrait]) -> None:
        for trait in other:
            self.add(trait)


@dataclass(init=False)
class Traits2:
    explicit: InternalTraitCollection
    type_implicit: InternalTraitCollection
    derived: InternalTraitCollection

    # @classmethod


@dataclass(init=False)
class Traits:
    items: dict[type[BaseTrait], BaseTrait] = field(default_factory=dict)

    def __init__(self, traits: set[BaseTrait] | None = None):
        super().__init__()
        self.items = {}
        if traits is not None:
            for trait in traits:
                self.add(trait)

    def find(self, trait_type: type[T]) -> T | None:
        return self.items.get(trait_type)  # type: ignore

    def add(self, item: BaseTrait, clobber_existing: bool = True) -> None:
        if type(item) == GenericBoundTrait:
            existing_generic_bound_trait = self.find(GenericBoundTrait)
            assert existing_generic_bound_trait is not None
            combined_bound_trait = existing_generic_bound_trait.merge_copy(item)
            self.items[GenericBoundTrait] = combined_bound_trait
            return
        if clobber_existing or type(item) not in self.items:
            self.items[type(item)] = item
            return
        raise SimileTraitError(f"Trait of type {type(item)} already exists in the collection.")

    def remove(self, item: BaseTrait) -> None:
        if type(item) in self.items and self.items[type(item)] == item:
            del self.items[type(item)]

    def update(self, other: set[BaseTrait]) -> None:
        for trait in other:
            self.add(trait)

    def normalize(self) -> None:
        # Rules (TODO verify with spec):
        # Domain Empty - DomainTrait with no values => Remove DomainTrait
        if domain_trait := self.find(DomainTrait):
            if len(domain_trait.values) == 0:
                self.remove(domain_trait)

        # Literal Implies a Domain - Literal + no DomainTrait => DomainTrait with one literal value
        if literal_trait := self.find(LiteralTrait):
            if not self.find(DomainTrait):
                self.add(DomainTrait(values=frozenset([literal_trait.value])))

        # Literal within Domain - Literal + DomainTrait without Literal => DomainTrait with literal value added
        if literal_trait := self.find(LiteralTrait):
            if domain_trait := self.find(DomainTrait):
                if literal_trait.value not in domain_trait.values:
                    new_domain_values = frozenset(domain_trait.values) | frozenset([literal_trait.value])
                    self.add(DomainTrait(values=new_domain_values))
        # All Domain objects must have the same type
        if domain_trait := self.find(DomainTrait):
            first_type = type(next(iter(domain_trait.values), None))
            for value in domain_trait.values:
                if type(value) != first_type:
                    raise SimileTraitError(f"DomainTrait values must all be of the same (python) type, but found {first_type} and {type(value)} in {domain_trait.values}")

        # Orderable Domain with/without Min/Max
        # - DomainTrait + Orderable + Min/MaxTrait where domain has a value smaller/larger => widened Min/MaxTrait
        # - DomainTrait + Orderable => Min/MaxTrait
        if (domain_trait := self.find(DomainTrait)) and self.find(OrderableTrait):
            if domain_trait.get_value_type() in set(get_args(SimileLiteralAsPythonOrderable)):
                if min_trait := self.find(MinTrait):
                    min_value = min(domain_trait.values)  # type: ignore
                    try:
                        if min_value < min_trait.value:  # type: ignore
                            self.add(MinTrait(value=min_value))  # type: ignore
                    except TypeError:
                        raise SimileTraitError(f"MinTrait value type {type(min_trait.value)} does not match DomainTrait value type {type(min_value)}")

                if max_trait := self.find(MaxTrait):
                    max_value = max(domain_trait.values)  # type: ignore
                    try:
                        if max_value > max_trait.value:  # type: ignore
                            self.add(MaxTrait(value=max_value))  # type: ignore
                    except TypeError:
                        raise SimileTraitError(f"MaxTrait value type {type(max_trait.value)} does not match DomainTrait value type {type(max_value)}")

        # Min/Max implies Order - Min/MaxTrait => Orderable
        if self.find(MinTrait) or self.find(MaxTrait):
            if not self.find(OrderableTrait):
                self.add(OrderableTrait())

        # Full set - Unique + Size + Domain + Size==len(Domain) => Total
        if self.find(EmptyTrait) is None and self.find(UniqueTrait) and (size_trait := self.find(SizeTrait)) and (domain_trait := self.find(DomainTrait)):
            if size_trait.size == len(domain_trait.values):
                self.add(TotalTrait())

        # Empty Size - Size == 0 => Empty
        if size_trait := self.find(SizeTrait):
            if size_trait.size == 0:
                self.add(EmptyTrait())

        # Non-empty Size - Size != 0 + Empty => remove Empty
        if size_trait := self.find(SizeTrait):
            if size_trait.size != 0:
                self.remove(EmptyTrait())

        # Size implies Iterable - Size => Iterable
        if self.find(SizeTrait):
            self.add(IterableTrait())

        # Orderable Literal is Min/Max - Literal + Orderable + no Min/Max => Min/Max with literal value
        if literal_trait := self.find(LiteralTrait):
            if self.find(OrderableTrait):
                if literal_trait.value not in set(get_args(SimileLiteralAsPythonOrderable)):
                    raise SimileTraitError(f"LiteralTrait value {literal_trait.value} is not orderable, but OrderableTrait is present")
                if not self.find(MinTrait):
                    self.add(MinTrait(value=literal_trait.value))  # type: ignore
                if not self.find(MaxTrait):
                    self.add(MaxTrait(value=literal_trait.value))  # type: ignore

        # TODO write down trait-trait dependencies
        raise NotImplementedError

    def check_compatible(self) -> None:
        # Check if specific traits are incompatible with one another (ex. max below min)
        raise NotImplementedError

    def merge_copy(self, other: Traits, behaviour: MergeTraitBehaviour = MergeTraitBehaviour.PREFER_LEFT) -> Traits:
        # Merging traits generally takes the widest possible value (union of the underlying sets)
        # But some traits may actually narrow upon merging with specific operations (ex. an intersection of two sets with different domains)
        # So we need to carefully evaluate what needs narrowing and what needs widening
        #
        # Generally used for when users define overriding traits, so we defer to user's judgement as a base and verify after
        # TODO think about how this actually used - if we just use it for trait applications and casting with traits,
        # then we should define a proper semantics - maybe we dont actually want to merge a copy, but instead repeatedly
        # add (and clobber) traits. For example:
        # x: int
        #    trait min = 9
        #
        # This should still keep the orderable trait, and if x already had a domain from 0-10, we restrict that domain
        # What is the responsibility of normalization, and what is the responsibility of merging? Maybe we shouldnt even
        # have a merge function, but let callers resolve their own behaviour. Or rather, we should define two methods here:
        # cast_with_trait and trait_application, corresponding to the methods that the actual types have

        traits = Traits()
        traits_to_add = Traits()
        match behaviour:
            case MergeTraitBehaviour.PREFER_LEFT:
                traits.items = copy(self.items)
                traits_to_add.items = copy(other.items)
            case MergeTraitBehaviour.PREFER_RIGHT:
                traits.items = copy(other.items)
                traits_to_add.items = copy(self.items)

        # Narrowing merges:
        # - Two equal literals remain the same literal, else widen to a domain with both literals
        if base_literal_trait := self.find(LiteralTrait):
            if addon_literal_trait := other.find(LiteralTrait):
                if base_literal_trait.value == addon_literal_trait.value:
                    traits.add(base_literal_trait)
                else:
                    traits.add(DomainTrait(values=frozenset([base_literal_trait.value, addon_literal_trait.value])))

        # - MinTrait takes the min of both
        if base_min_trait := self.find(MinTrait):
            if addon_min_trait := other.find(MinTrait):
                new_min_value = min(base_min_trait.value, addon_min_trait.value)
                traits.add(MinTrait(value=new_min_value))

        # - MaxTrait takes the max of both
        if base_max_trait := self.find(MaxTrait):
            if addon_max_trait := other.find(MaxTrait):
                new_max_value = max(base_max_trait.value, addon_max_trait.value)
                traits.add(MaxTrait(value=new_max_value))

        # - DomainTrait unions with DomainTrait
        if base_domain_trait := self.find(DomainTrait):
            if addon_domain_trait := other.find(DomainTrait):
                new_domain_values = frozenset(base_domain_trait.values) | frozenset(addon_domain_trait.values)
                traits.add(DomainTrait(values=new_domain_values))
        # - ...
        traits.normalize()
        return traits


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
