from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type, ClassVar, Self
from warnings import deprecated
from pathlib import Path

from src.mod.data.types.error import SimileTypeError
from src.mod.data.types.base import BaseType
from src.mod.data.traits import (
    BaseTrait,
    IterableTrait,
    DomainTrait,
    SizeTrait,
    TotalOnDomainTrait,
    ManyToOneTrait,
    LiteralTrait,
    RelationalDomainTrait,
    TreatAsExprTrait,
    GenericBoundTrait,
)

if TYPE_CHECKING:
    from src.mod.data.symbol_table.entry import SymbolTableIdentifierEntry, ScopeTableEntry


@dataclass
class AnyType_(BaseType):

    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, AnyType_)

    def _is_subtype(self, other: BaseType) -> bool:
        return False

    def base_traits(self) -> set[BaseTrait]:
        return set()

    def check_incompatible_traits(self) -> None:
        return None


@dataclass
class EmptyCollectionType(BaseType):
    def _is_eq_type(self, other: BaseType) -> bool:
        return isinstance(other, EmptyCollectionType)

    def _is_subtype(self, other: BaseType) -> bool:
        # Assuming that this type is only called within the context of an empty collection
        # it can become any possible type
        # TODO add the formalization rules for this into the spec
        return True

    def base_traits(self) -> set[BaseTrait]:
        return set()

    def check_incompatible_traits(self) -> None:
        return None


@dataclass
class GenericType(BaseType):
    """Generic types are used primarily for resolving generic procedures/functions into a specific type based on context.

    IDs are only locally valid (i.e., introduced by a procedure argument and used by a procedure's return value).
    Generic types may reuse IDs in outer scopes.
    """

    symbol_id: int | None = None
    scope_id: int | None = None
    compatible_traits: ClassVar[set[Type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        GenericBoundTrait,
    }

    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, GenericType):
            return False
        # return self.id_ == other.id_ and self.trait_collection.generic_bound_trait == other.trait_collection.generic_bound_trait
        return self.traits.find(GenericBoundTrait) == other.traits.find(GenericBoundTrait)

    def _is_subtype(self, other: BaseType) -> bool:
        self_generic_bound_trait = self.traits.find(GenericBoundTrait)
        if self_generic_bound_trait is None:
            return False  # effectively the AnyType when its not bound

        if not isinstance(other, GenericType):
            # Comparing generic <= concrete means ALL bound types must be a subtype of the concrete
            for self_bound in self_generic_bound_trait.bound_types:
                if not self_bound.is_subtype(other):
                    return False
            return True

        other_generic_bound_trait = other.traits.find(GenericBoundTrait)
        if other_generic_bound_trait is None:
            return True

        # A generic type is a subtype only if all its bound types are subtypes of at least one of the other's bound types
        for self_bound in self_generic_bound_trait.bound_types:
            for other_bound in other_generic_bound_trait.bound_types:
                if self_bound.is_subtype(other_bound):
                    break
            else:
                return False  # no break occurred, so self_bound is not a subtype of any other_bound
        return True

    def base_traits(self) -> set[BaseTrait]:
        return set()

    def add_symbol_info(self, symbol: SymbolTableIdentifierEntry) -> None:
        # TODO just take in the symbol table entry??

        # if self.symbol_id is not None or self.scope_id is not None:
        #     raise SimileTypeError(f"Generic type {self} already has a symbol ID/scope ID. Cannot add symbol info ({symbol}) to ID.")

        self.symbol_id = symbol.id_
        self.scope_id = symbol.scope

    def match_generic_types(self, concrete_type: BaseType) -> dict[tuple[int, int], BaseType]:
        # TODO Generic bound trait checks here - if bound traits exist, concrete type must be one of those bound traits, else err
        return {self.id_(): concrete_type}

    def replace_generic_types(self, generic_to_concrete_type_map: dict[tuple[int, int], BaseType]) -> BaseType:  # type: ignore
        if self.symbol_id is None or self.scope_id is None:
            raise SimileTypeError(f"Generic type {self} does not have a symbol ID/scope ID. Cannot replace with concrete type.")

        key = (self.symbol_id, self.scope_id)
        return generic_to_concrete_type_map.get(key, self)

    def extract_generic_types(self) -> list[GenericType]:
        return [self]

    def id_(self) -> tuple[int, int]:
        if self.symbol_id is None or self.scope_id is None:
            raise SimileTypeError(f"Generic type {self} does not have a symbol ID/scope ID.")
        return self.symbol_id, self.scope_id


@dataclass
@deprecated("Do we actually need this type?")
class DeferToSymbolTable(BaseType):
    """Types dependent on this will not be resolved until the analysis phase.

    Any type-checking functions called on unresolved types should raise an error."""

    lookup_symbol_entry: SymbolTableIdentifierEntry
    """Entry corresponding to the initial identifier"""

    params: list[BaseType]
    """In case the identifier is a generic type (or otherwise expects parameters)"""

    def _is_eq_type(self, other: BaseType) -> bool:
        raise SimileTypeError("Cannot compare DeferToSymbolTable types before resolution")

    def _is_subtype(self, other: BaseType) -> bool:
        raise SimileTypeError("Cannot compare DeferToSymbolTable types before resolution")

    def base_traits(self) -> set[BaseTrait]:
        return set()


@dataclass
class ImportedSymbol(BaseType):
    imported_symbol_entry: SymbolTableIdentifierEntry
    source_file: Path  # use to dedupe multiple imports of the same symbol

    def base_traits(self) -> set[BaseTrait]:
        return set()

    def match_generic_types(self, concrete_type: BaseType) -> dict[tuple[int, int], BaseType]:
        if not isinstance(concrete_type, ImportedSymbol):
            raise SimileTypeError(f"Cannot match generic types for ImportedSymbol with non-ImportedSymbol {concrete_type}")

        return self.imported_symbol_entry.declared_type.match_generic_types(concrete_type.imported_symbol_entry.declared_type)

    def replace_generic_types(self, generic_to_concrete_type_map: dict[tuple[int, int], BaseType]) -> Self:
        new_declared_type = self.imported_symbol_entry.declared_type.replace_generic_types(generic_to_concrete_type_map)
        if new_declared_type == self.imported_symbol_entry.declared_type:
            return self
        # TODO this is a bit of a hack, but we need to create a new symbol table entry with the new declared type
        new_imported_symbol_entry = SymbolTableIdentifierEntry(
            id_=self.imported_symbol_entry.id_,
            scope=self.imported_symbol_entry.scope,
            name=self.imported_symbol_entry.name,
            context=self.imported_symbol_entry.context,
            declared_type=new_declared_type,
        )
        return type(self)(new_imported_symbol_entry, self.source_file)

    def extract_generic_types(self) -> list[GenericType]:
        return self.imported_symbol_entry.declared_type.extract_generic_types()


@dataclass
class ModuleImports(BaseType):
    """Type to represent importing these objects into the module namespace

    Any type-checking functions called on environments (which is what this dict really is) should raise an error."""

    # Function names and types are held within this scope of the symbol table
    scope: ScopeTableEntry
    source_file: Path

    def base_traits(self) -> set[BaseTrait]:
        return set()


@dataclass
class TypeOfType(BaseType):
    type_of: BaseType

    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, TypeOfType):
            return False
        return self.type_of == other.type_of

    def base_traits(self) -> set[BaseTrait]:
        return set()

    def match_generic_types(self, concrete_type: BaseType) -> dict[tuple[int, int], BaseType]:
        return self.type_of.match_generic_types(concrete_type)

    def replace_generic_types(self, generic_to_concrete_type_map: dict[tuple[int, int], BaseType]) -> Self:
        new_type_of = self.type_of.replace_generic_types(generic_to_concrete_type_map)
        if new_type_of == self.type_of:
            return self
        return type(self)(new_type_of)

    def extract_generic_types(self) -> list[GenericType]:
        return self.type_of.extract_generic_types()


@dataclass
class TraitType(BaseType):
    """Used to lift a trait into a type"""  # TODO remove?

    trait_name: str | None

    def base_traits(self) -> set[BaseTrait]:
        return set()
