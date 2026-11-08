from src.mod.data import types
from functools import singledispatch


@singledispatch
def type_to_source(type_: types.BaseType) -> str:
    raise Exception(f"Compiler error: missing type_to_source definition for AST type {type_.__class__.__name__}", type_)


@type_to_source.register
def _(type_: types.RecordType) -> str:
    parameterized_types = ", ".join(f"{field_name}: {type_to_source(field_type)}" for field_name, field_type in type_.fields.items())
    return f"record[{parameterized_types}]"


@type_to_source.register
def _(type_: types.ProcedureType) -> str:
    return f"procedure[{type_to_source(type_.arg_types)}, {type_to_source(type_.return_type)}]"


@type_to_source.register
def _(type_: types.BoolType) -> str:
    return "bool"


@type_to_source.register
def _(type_: types.AnyType_) -> str:
    return "any"


@type_to_source.register
def _(type_: types.GenericType) -> str:
    # TODO store the friendly name back in GenericType
    return f"T_scope{type_.scope_id}_symbol{type_.symbol_id}"


@type_to_source.register
def _(type_: types.ImportedSymbol) -> str:
    return type_to_source(type_.imported_symbol_entry.declared_type)


@type_to_source.register
def _(type_: types.TypeOfType) -> str:
    return f"type[{type_to_source(type_.type_of)}]"


@type_to_source.register
def _(type_: types.TraitType) -> str:
    return "trait"


@type_to_source.register
def _(type_: types.NoneType_) -> str:
    return "none"


@type_to_source.register
def _(type_: types.StringType) -> str:
    return "string"


@type_to_source.register
def _(type_: types.IntType) -> str:
    return "int"


@type_to_source.register
def _(type_: types.FloatType) -> str:
    return "float"


@type_to_source.register
def _(type_: types.SetType) -> str:
    return f"set[{type_to_source(type_.element_type)}]"


@type_to_source.register
def _(type_: types.RelationType) -> str:
    return f"relation[{type_to_source(type_.left)}, {type_to_source(type_.right)}]"


@type_to_source.register
def _(type_: types.BagType) -> str:
    return f"bag[{type_to_source(type_.element_type_)}]"


@type_to_source.register
def _(type_: types.SequenceType) -> str:
    return f"sequence[{type_to_source(type_.element_type_)}]"


@type_to_source.register
def _(type_: types.EnumType) -> str:
    return "enum"


@type_to_source.register
def _(type_: types.TupleType) -> str:
    parameterized_types = ", ".join(type_to_source(item) for item in type_.items)
    return f"tuple[{parameterized_types}]"
