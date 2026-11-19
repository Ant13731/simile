from __future__ import annotations
from dataclasses import dataclass, field
from collections import OrderedDict
from typing import ClassVar, TYPE_CHECKING, Self
from loguru import logger

from src.mod.data.types.error import SimileTypeError
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
)

from src.mod.data.types.set_ import SetType
from src.mod.data.types.base import BaseType
from src.mod.data.types.primitive import NoneType_, StringType
from src.mod.data.types.tuple_ import TupleType
from src.mod.data.types.meta import GenericType
from src.mod.data.types.typing_rule_decorator import typing_rule

if TYPE_CHECKING:
    from src.mod.data.symbol_table.entry import SymbolTableIdentifierEntry, ScopeTableEntry


@dataclass
class RecordType(BaseType):
    # Internally a (many-to-one) (total on defined fields) function
    name: str
    fields: dict[str, BaseType]
    lookup_scope_entry: ScopeTableEntry | None = None  # Where the record was defined, used to look up the fields in the symbol table
    compatible_traits: ClassVar[set[type[BaseTrait]]] = {
        *BaseType.compatible_traits,
        LiteralTrait,
        # inherits from set traits
        IterableTrait,
        SizeTrait,
        # inherits from relational traits
        ManyToOneTrait,
        TotalOnDomainTrait,
        RelationalDomainTrait,
    }

    def __post_init__(self):
        for field, typ in self.fields.items():
            if isinstance(typ, GenericType):
                raise SimileTypeError(
                    f"Generics not currently supported for record types. Please define a concrete type for all fields in the record. Field {field} has type {typ}"
                )

    def add_scope_entry(self, scope_entry: ScopeTableEntry) -> None:
        if self.lookup_scope_entry is not None:
            raise SimileTypeError(f"RecordType {self.name} already has a lookup scope entry: {self.lookup_scope_entry}")
        self.lookup_scope_entry = scope_entry

    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, RecordType):
            return False
        return all(
            self_field._is_eq_type(other_field)
            for self_field, other_field in zip(
                self.fields.values(),
                other.fields.values(),
            )
        )

    @typing_rule("Sub Record")
    def _is_subtype(self, other: BaseType) -> bool:
        if not isinstance(other, RecordType):
            return False

        for name in other.fields:
            # Records are only subtypes if they have at least all the same fields as other
            if name not in self.fields:
                return False

            # Fields that do match must be subtypes
            if not self.fields[name].is_subtype(other.fields[name]):
                return False

        return True

    def base_traits(self) -> set[BaseTrait]:
        return {
            RelationalDomainTrait(set(self.fields.keys())),
            SizeTrait(len(self.fields)),
            ManyToOneTrait(),
            IterableTrait(),
            TotalOnDomainTrait(),
        }

    def access(self, field_name: str) -> BaseType:
        # TODO how to handle generics? For now dont allow in record types
        # FIXME see above comments and __post_init__ on generics
        if field_name not in self.fields:
            raise KeyError(f"RecordType has no field named '{field_name}'")
        return self.fields[field_name]


@dataclass
class ProcedureType(BaseType):
    arg_types: TupleType
    return_type: BaseType
    compatible_traits: ClassVar[set[type[BaseTrait]]] = {TreatAsExprTrait}

    def _is_eq_type(self, other: BaseType) -> bool:
        if not isinstance(other, ProcedureType):
            return False
        return all(
            self_arg.is_eq_type(other_arg)
            for self_arg, other_arg in zip(
                self.arg_types.items,
                other.arg_types.items,
            )
        ) and self.return_type.is_eq_type(
            other.return_type,
        )

    @typing_rule("Sub Function")
    def _is_subtype(self, other: BaseType) -> bool:
        if not isinstance(other, ProcedureType):
            return False

        args_are_supertype = all(
            other_arg.is_subtype(self_arg)
            for self_arg, other_arg in zip(
                self.arg_types.items,
                other.arg_types.items,
            )
        )

        return args_are_supertype and self.return_type.is_subtype(other.return_type)

    def call(self, arg_types: list[BaseType]) -> BaseType:
        from src.mod.pipeline.printers.type_ import type_to_source

        if len(arg_types) != len(self.arg_types.items):
            raise SimileTypeError(f"Procedure called with incorrect number of arguments. Expected {len(self.arg_types.items)}, got {len(arg_types)}")

        for i, (provided_type, expected_type) in enumerate(zip(arg_types, self.arg_types.items)):
            if not provided_type.is_subtype(expected_type):
                raise SimileTypeError(f"Procedure argument {i} expected type {type_to_source(expected_type)}, got {type_to_source(provided_type)}")

        generic_to_concrete_types = self.match_generic_types(ProcedureType(TupleType(arg_types), NoneType_()))
        concrete_procedure_type = self.replace_generic_types(generic_to_concrete_types)
        return concrete_procedure_type.return_type

    def base_traits(self) -> set[BaseTrait]:
        return set()

    def match_generic_types(self, concrete_type: BaseType) -> dict[tuple[int, int], BaseType]:
        if not isinstance(concrete_type, ProcedureType):
            raise SimileTypeError(f"Cannot match generic types for ProcedureType with non-ProcedureType {concrete_type}")

        try:
            return self.arg_types.match_generic_types(concrete_type.arg_types)
        except SimileTypeError as e:
            raise SimileTypeError(f"Cannot match generic types for ProcedureType args: {e}") from e

    def replace_generic_types(self, generic_to_concrete_type_map: dict[tuple[int, int], BaseType]) -> Self:
        new_arg_types = self.arg_types.replace_generic_types(generic_to_concrete_type_map)
        assert isinstance(new_arg_types, TupleType), f"Expected new_arg_types to be a TupleType, got {new_arg_types}"
        new_return_type = self.return_type.replace_generic_types(generic_to_concrete_type_map)
        if leftover_generics := new_return_type.extract_generic_types():
            for leftover_generic in leftover_generics:
                if leftover_generic.id_() not in generic_to_concrete_type_map:
                    # TODO this doesnt work with bag.sim/map_b
                    logger.warning(
                        f"Generic return type {self.return_type} does not have a matching argument type to determine its concrete return type. Leftover generic {leftover_generic} after matching against {generic_to_concrete_type_map}"
                    )
                    # raise SimileTypeError(
                    #     f"Generic return type {self.return_type} does not have a matching argument type to determine its concrete return type. Leftover generic {leftover_generic} after matching against {generic_to_concrete_type_map}"
                    # )
        return type(self)(new_arg_types, new_return_type)

    def extract_generic_types(self) -> list[GenericType]:
        return self.arg_types.extract_generic_types() + self.return_type.extract_generic_types()
