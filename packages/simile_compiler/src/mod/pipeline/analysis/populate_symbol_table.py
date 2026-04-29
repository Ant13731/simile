import pathlib
from typing_extensions import OrderedDict


from src.mod.data import ast_
from src.mod.data.types import BaseType, ProcedureType, RecordType, ModuleImports, SimileTypeError
from src.mod.data.symbol_table import SymbolTable, IdentifierContext, ScopeContext

from src.mod.pipeline.analysis.ambiguous_quantification import find_unbound_identifiers
from src.mod.pipeline.parser import parse, ParseError


class ParseImportError(Exception):
    pass


def populate_symbol_table(ast: ast_.ASTNode) -> SymbolTable:
    """Populates the symbol table with all identifiers in the AST."""

    symbol_table = SymbolTable()
    symbol_table.add_scope(ScopeContext.BASE)
    _populate_symbol_table_aux(symbol_table, ast)
    return symbol_table


def _populate_symbol_table_aux(symbol_table: SymbolTable, node: ast_.ASTNode) -> None:
    match node:
        # Scopes
        case ast_.If(condition, body, else_body) | ast_.ElseIf(condition, body, else_body):
            symbol_table.add_scope(ScopeContext.CONDITIONAL)
            _populate_symbol_table_aux(symbol_table, condition)
            _populate_symbol_table_aux(symbol_table, body)
            _populate_symbol_table_aux(symbol_table, else_body)
            symbol_table.pop_scope_level()
            return
        case ast_.Else(body):
            symbol_table.add_scope(ScopeContext.CONDITIONAL)
            _populate_symbol_table_aux(symbol_table, body)
            symbol_table.pop_scope_level()
            return
        case ast_.While(condition, body):
            symbol_table.add_scope(ScopeContext.LOOP)
            _populate_symbol_table_aux(symbol_table, condition)
            _populate_symbol_table_aux(symbol_table, body)
            symbol_table.pop_scope_level()
            return
        case ast_.For(iterable_names, iterable, body):
            symbol_table.add_scope(ScopeContext.LOOP)

            _populate_loop_parameters(symbol_table, iterable_names)

            _populate_symbol_table_aux(symbol_table, iterable)
            _populate_symbol_table_aux(symbol_table, body)
            symbol_table.pop_scope_level()
            return
        case ast_.QualifiedQuantifier(bound_identifiers, predicate, expression, _):
            symbol_table.add_scope(ScopeContext.QUANTIFICATION)

            _populate_loop_parameters(symbol_table, bound_identifiers)

            _populate_symbol_table_aux(symbol_table, predicate)
            _populate_symbol_table_aux(symbol_table, expression)
            symbol_table.pop_scope_level()
            return
        case ast_.Quantifier(predicate, expression, _):
            symbol_table.add_scope(ScopeContext.QUANTIFICATION)

            # Stores bound identifiers within the quantifier! Side effect needed to work with promote_quantifiers_to_qualified
            _populate_loop_parameters(symbol_table, find_unbound_identifiers(symbol_table, node))

            _populate_symbol_table_aux(symbol_table, predicate)
            _populate_symbol_table_aux(symbol_table, expression)
            symbol_table.pop_scope_level()
            return
        case ast_.ProcedureDef(name, params, body, return_type):
            params_dict: dict[str, BaseType] = OrderedDict()
            for param in params:
                if not isinstance(param.name, ast_.Identifier):
                    raise SimileTypeError(f"Invalid procedure parameter name (must be an identifier): {param.name}", param)
                params_dict[param.name.name] = _ast_to_type(symbol_table, param.type_)
            symbol_table.add_symbol(
                name.name,
                IdentifierContext.PROCEDURE,
                ProcedureType(params_dict, _ast_to_type(symbol_table, return_type)),
            )

            symbol_table.add_scope(ScopeContext.PROCEDURE)

            for param_name, param_type in params_dict.items():
                symbol_table.add_symbol(
                    param_name,
                    IdentifierContext.PROCEDURE_PARAMETER,
                    param_type,
                )
            _populate_symbol_table_aux(symbol_table, body)

            symbol_table.pop_scope_level()
            return
        case ast_.LambdaDef(params, predicate, expression):
            symbol_table.add_scope(ScopeContext.LAMBDA)
            _populate_symbol_table_aux(symbol_table, predicate)
            _populate_symbol_table_aux(symbol_table, expression)

            _populate_loop_parameters(symbol_table, params)

            symbol_table.pop_scope_level()
            return

        # Symbols
        # TODO check for enum def in all assignment statements
        case ast_.Assignment(ast_.Identifier(name), _):
            symbol_table.add_symbol(
                name,
                IdentifierContext.VARIABLE,
            )
        case ast_.Assignment(ast_.TypedName(ast_.Identifier(name), declared_type), _):
            symbol_table.add_symbol(
                name,
                IdentifierContext.VARIABLE,
                _ast_to_type(symbol_table, declared_type),
            )
        # case ast_.Assignment(ast_.StructAccess(struct, field), _):
        # case ast_.Assignment(ast_.TypedName(ast_.StructAccess(struct, field), _), _):
        case ast_.RecordDef(ast_.Identifier(name), items):
            fields: dict[str, BaseType] = OrderedDict()
            for item in items:
                if not isinstance(item.name, ast_.Identifier):
                    raise SimileTypeError(f"Invalid struct field name (must be an identifier): {item.name}", item)
                fields[item.name.name] = _ast_to_type(symbol_table, item.type_)

            symbol_table.add_symbol(
                name,
                IdentifierContext.RECORD,
                RecordType(fields=fields),
            )
        case ast_.Import(module_file_path, import_objects):
            _populate_from_import(symbol_table, import_objects, module_file_path)

    for child in node.children():
        _populate_symbol_table_aux(symbol_table, child)


def _populate_loop_parameters(
    symbol_table: SymbolTable,
    iterable_names: ast_.Identifier | ast_.MapletIdentifier | ast_.TupleIdentifier,
) -> None:
    if isinstance(iterable_names, ast_.Identifier):
        symbol_table.add_symbol(
            iterable_names.name,
            IdentifierContext.LOOP_VARIABLE,
        )
    elif isinstance(iterable_names, ast_.TupleIdentifier):
        for ident in iterable_names.flatten():
            _populate_loop_parameters(symbol_table, ident)
    else:
        raise SimileTypeError(f"Invalid for loop variable name (must be an identifier, maplet identifier, or tuple identifier): {iterable_names}", iterable_names)


def _populate_from_import(
    symbol_table: SymbolTable,
    import_objects: ast_.TupleIdentifier | ast_.None_ | ast_.ImportAll,
    module_file_path: str,
) -> None:
    # Read in imported file
    full_module_path = pathlib.Path(module_file_path).resolve(strict=True)
    with open(full_module_path, "r") as f:
        module_content = f.read()

    # Parse module content
    try:
        module_ast: ast_.Start = parse(module_content)
    except ParseError as e:
        raise ParseImportError(f"Module {module_file_path} does not contain a valid Simile module. Expected a single Start node at the top level.") from e

    if isinstance(module_ast.body, ast_.None_):
        return

    # Populate the module AST with types
    module_symbol_table = populate_symbol_table(module_ast)

    # Add module symbols to namespace
    match import_objects:
        case ast_.ImportAll():
            for symbol_table_entry in module_symbol_table.get_top_level_symbols():
                symbol_table.add_symbol(
                    symbol_table_entry.name,
                    symbol_table_entry.context,
                    symbol_table_entry.declared_type,
                )
        case ast_.None_():
            symbol_table.add_symbol(
                full_module_path.stem,
                IdentifierContext.MODULE_IMPORT,
                ModuleImports(module_symbol_table.get_top_level_symbols()),
            )
        case ast_.TupleIdentifier(identifiers):
            identifier_names = []
            for identifier in identifiers:
                if not isinstance(identifier, ast_.Identifier):
                    raise SimileTypeError(f"Invalid import type (must be an identifier): {identifier}", identifier)
                identifier_names.append(identifier.name)

            for symbol_table_entry in module_symbol_table.get_top_level_symbols():
                if symbol_table_entry.name in identifier_names:
                    symbol_table.add_symbol(
                        symbol_table_entry.name,
                        symbol_table_entry.context,
                        symbol_table_entry.declared_type,
                    )
