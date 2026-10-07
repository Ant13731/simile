from dataclasses import asdict
from copy import deepcopy

from src.mod.data import ast_
from src.mod.data.symbol_table import SymbolTable, SymbolTableIdentifierEntry
from src.mod.data.types import (
    BaseType,
    BoolType,
    GenericType,
    DeferToSymbolTable,
    StringType,
    IntType,
    FloatType,
    SetType,
    BagType,
    RelationType,
    SequenceType,
    TupleType,
    SimileTypeError,
    TypeOfType,
    ProcedureType,
    RecordType,
    EnumType,
    NoneType_,
    AnyType_,
    TraitType,
)
from src.mod.data.traits import Traits, MinTrait


class TypeAnnotationResolver:
    BUILT_IN_TYPES = {
        # primitive
        "int": IntType(),
        "float": FloatType(),
        "string": StringType(),
        "bool": BoolType(),
        # set
        "set": SetType(GenericType()),
        "sequence": SequenceType(GenericType()),
        "bag": BagType(GenericType()),
        "relation": RelationType(GenericType(), GenericType()),
        # meta
        "generic": GenericType(),
        "type": TypeOfType(GenericType()),
        "enum": EnumType(GenericType()),
        # variable length types, dont populate anything since they can take multiple (unknown) arguments
        "tuple": TupleType([]),
        "procedure": ProcedureType(TupleType([]), GenericType()),
        "record": RecordType({}),
        # type sugar
        "ℤ": SetType(IntType()),
        "ℕ": SetType(IntType(traits=Traits({MinTrait(0)}))),
        "ℕ₁": SetType(IntType(traits=Traits({MinTrait(1)}))),
        # traits as typed objects?
        # TODO how should we handle traits as first-class objects? I suppose they should just be an expr?
        "trait": TraitType(None),
    }

    # limited form of the below type synthesizer (which should not need to encounter type annotations)
    # this should be accessible to populate_symbol_table though
    @classmethod
    def resolve_type_annotation(cls, ast: ast_.Type_ | ast_.ASTNode, symbol_table: SymbolTable) -> BaseType:
        resolved_type_params: list[BaseType] = []
        if isinstance(ast, ast_.Type_):
            resolved_type_params = [cls.resolve_type_annotation(type_param, symbol_table) for type_param in ast.generics]
            ast = ast.type_

        match ast:
            # Used while populating the symbol table
            case ast_.TupleLiteral(type_params):
                if len(resolved_type_params) != 0:
                    raise SimileTypeError("Cannot provide parameters to a tuple type")
                resolved_type_params = [cls.resolve_type_annotation(type_param, symbol_table) for type_param in type_params]
                return TupleType(resolved_type_params)
            case ast_.Identifier(symbol_table_name):
                symbol_table_entry = symbol_table.lookup_identifier(symbol_table_name)
                # special case to populate generic type ids with their identifier values as initialized
                declared_type = deepcopy(symbol_table_entry.declared_type)
                if isinstance(declared_type, GenericType):
                    declared_type.add_symbol_info(symbol_table_entry)
                return cls._resolve_generic_type_params(declared_type, resolved_type_params)
            # Used for type synthesis after the symbol table is populated
            case ast_.TupleSymbol(type_params):
                if len(resolved_type_params) != 0:
                    raise SimileTypeError("Cannot provide parameters to a tuple type")
                resolved_type_params = [cls.resolve_type_annotation(type_param, symbol_table) for type_param in type_params]
                return TupleType(resolved_type_params)
            case ast_.Symbol(symbol_table_entry):
                return cls._resolve_generic_type_params(symbol_table_entry.declared_type, resolved_type_params)
            # Special notation for relation types
            # TODO not allowed by parser for now?
            case ast_.RelationOp(left, right, op):
                if len(resolved_type_params) != 0:
                    raise SimileTypeError(f"Infix relation operator type annotation cannot have parameters, got {len(resolved_type_params)}: {resolved_type_params}", ast)
                left_type = cls.resolve_type_annotation(left, symbol_table)
                right_type = cls.resolve_type_annotation(right, symbol_table)
                rel_type = RelationType(left_type, right_type)
                rel_type.apply_traits_from_relation_operator(op)
                return rel_type
            # TODO record types (user identified types) with generics? disallow for now

        raise SimileTypeError(f"Failed to resolve type annotation", ast)

    @classmethod
    def _resolve_generic_type_params(cls, base_type: BaseType, type_params: list[BaseType]) -> BaseType:
        if isinstance(base_type, TupleType):
            raise SimileTypeError(
                f"Cannot apply generic type parameters to a tuple type. Use the tuple literal syntax instead. (got base type {base_type} with params {type_params})"
            )

        if isinstance(base_type, SequenceType):
            if len(type_params) != 1:
                raise SimileTypeError(f"Sequence type annotation must have exactly 1 parameter, got {len(type_params)}: {type_params}")
            return SequenceType(type_params[0])
        if isinstance(base_type, BagType):
            if len(type_params) != 1:
                raise SimileTypeError(f"Bag type annotation must have exactly 1 parameter, got {len(type_params)}: {type_params}")
            return BagType(type_params[0])
        if isinstance(base_type, RelationType):
            if len(type_params) != 2:
                raise SimileTypeError(f"Relation type annotation must have exactly 2 parameters, got {len(type_params)}: {type_params}")
            return RelationType(type_params[0], type_params[1])
        if isinstance(base_type, SetType):
            if len(type_params) != 1:
                raise SimileTypeError(f"Set type annotation must have exactly 1 parameter, got {len(type_params)}: {type_params}")
            return SetType(type_params[0])

        if isinstance(base_type, TypeOfType):
            if len(type_params) != 1:
                # ignore for now
                return base_type
                # raise SimileTypeError(f"TypeOfType type annotation must have exactly 1 parameter, got {len(type_params)}: {type_params}")
            return TypeOfType(type_params[0])
        if isinstance(base_type, ProcedureType):
            if len(type_params) != 2:
                raise SimileTypeError(
                    f"Procedure type annotation must have exactly 2 parameters (multiple arguments get grouped into a tuple), got {len(type_params)}: {type_params}",
                )
            if not isinstance(type_params[0], TupleType):
                raise SimileTypeError(
                    f"Procedure type annotation first parameter must be a tuple of argument types, got {type_params[0]}",
                )
            return ProcedureType(type_params[0], type_params[1])

        if isinstance(base_type, EnumType):
            if len(type_params) > 1:
                raise SimileTypeError(f"Generic type annotation must have either 0 or 1 parameters, got {len(type_params)}: {type_params}")
            if len(type_params) == 1:
                return EnumType(type_params[0])
            return EnumType()

        # TODO record types with generics? disallow for now...
        # Types that expect no generic params
        if len(type_params) == 0:
            return base_type

        raise SimileTypeError(f"Cannot apply generic type parameters to non-generic type: {base_type}")
