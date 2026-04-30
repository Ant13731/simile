from dataclasses import dataclass, fields
import pathlib
from typing_extensions import OrderedDict


from src.mod.data import ast_
from src.mod.data.symbol_table.error import SymbolTableError
from src.mod.data.types import BaseType, ProcedureType, RecordType, ModuleImports, SimileTypeError
from src.mod.data.symbol_table import SymbolTable, IdentifierContext, ScopeContext

from src.mod.pipeline.parser import parse, ParseError


class ParseImportError(Exception):
    pass


def populate_symbol_table(ast: ast_.ASTNode) -> SymbolTable:
    """Populates the symbol table with all identifiers in the AST.
    SIDE EFFECT: Transforms Identifiers within the ast into symbol-table assigned Symbols
    """

    symbol_table = SymbolTable()
    symbol_table.add_scope(ScopeContext.BASE)
    symbol_table_populator = PopulateSymbolTable(symbol_table)
    symbol_table_populator.populate(ast)
    return symbol_table


class PopulateSymbolTable:
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self._parents: list[ast_.ASTNode] = []

    def populate(self, ast: ast_.ASTNode) -> ast_.ASTNode:
        self._parents.append(ast)
        new_ast_node, continue_populating = self._populate_aux(ast)
        if new_ast_node is not None:
            ast = new_ast_node

        if not continue_populating:
            return ast

        for f in fields(ast):
            field_value = getattr(ast, f.name)
            if isinstance(field_value, list):
                new_list = []
                for item in field_value:
                    new_list.append(self.populate(item))
                setattr(ast, f.name, new_list)
            else:
                setattr(ast, f.name, self.populate(field_value))
        self._parents.pop()
        return ast

    def _populate_aux(self, ast: ast_.ASTNode) -> tuple[ast_.ASTNode | None, bool]:
        """Returns: (Node to replace if not None, whether to continue populating children)"""
        match ast:
            # Scopes
            case ast_.If(condition, body, else_body):
                self.symbol_table.add_scope(ScopeContext.CONDITIONAL)
                _condition = self.populate(condition)
                _body = self.populate(body)
                _else_body = self.populate(else_body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_else_body, ast_.Else | ast_.ElseIf | ast_.None_)
                return ast_.If(_condition, _body, _else_body), False

            case ast_.ElseIf(condition, body, else_body):
                self.symbol_table.add_scope(ScopeContext.CONDITIONAL)
                _condition = self.populate(condition)
                _body = self.populate(body)
                _else_body = self.populate(else_body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_else_body, ast_.Else | ast_.ElseIf | ast_.None_)
                return ast_.ElseIf(_condition, _body, _else_body), False

            case ast_.Else(body):
                self.symbol_table.add_scope(ScopeContext.CONDITIONAL)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                return ast_.Else(_body), False

            case ast_.While(condition, body):
                self.symbol_table.add_scope(ScopeContext.LOOP)
                _condition = self.populate(condition)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                return ast_.While(_condition, _body), False

            case ast_.For(iterable_names, iterable, body):
                self.symbol_table.add_scope(ScopeContext.LOOP)
                self._populate_loop_parameters(iterable_names)
                _iterable_symbols = self._convert_identifier_to_symbol(iterable_names)
                _iterable = self.populate(iterable)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                return ast_.For(_iterable_symbols, _iterable, _body), False
            case ast_.QualifiedQuantifier(bound_identifiers, predicate, expression, op_type):
                self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                self._populate_loop_parameters(bound_identifiers)
                _iterable_symbols = self._convert_identifier_to_symbol(bound_identifiers)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)
                self.symbol_table.pop_scope_level()

                assert isinstance(_predicate, ast_.ListOp)
                return ast_.QualifiedQuantifier(_iterable_symbols, _predicate, _expression, op_type), False

            case ast_.Quantifier(predicate, expression, op_type):
                self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                unbound_identifiers = self._find_unbound_identifiers(ast)
                self._populate_loop_parameters(unbound_identifiers)
                _iterable_symbols = self._convert_identifier_to_symbol(unbound_identifiers)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)
                self.symbol_table.pop_scope_level()

                assert isinstance(_predicate, ast_.ListOp)
                return ast_.QualifiedQuantifier(_iterable_symbols, _predicate, _expression, op_type), False

            case ast_.ProcedureDef(name, params, body, return_type):
                params_dict: dict[str, BaseType] = OrderedDict()
                for param in params:
                    if not isinstance(param.name, ast_.Identifier):
                        raise SimileTypeError(f"Invalid procedure parameter name (must be an identifier): {param.name}", param)
                    params_dict[param.name.name] = _ast_to_type(self.symbol_table, param.type_)
                self.symbol_table.add_symbol(
                    name.name,
                    IdentifierContext.PROCEDURE,
                    ProcedureType(params_dict, _ast_to_type(self.symbol_table, return_type)),
                )
                _name_symbol = self._convert_identifier_to_symbol(name)

                self.symbol_table.add_scope(ScopeContext.PROCEDURE)

                _params_symbols = []
                for param_name, param_type in params_dict.items():
                    self.symbol_table.add_symbol(
                        param_name,
                        IdentifierContext.PROCEDURE_PARAMETER,
                        param_type,
                    )
                    _params_symbols.append(self._convert_identifier_to_symbol(ast_.Identifier(param_name)))

                _body = self.populate(body)

                self.symbol_table.pop_scope_level()
                return ast_.ProcedureSymbolDef(_name_symbol, _params_symbols, _body), False
            case ast_.LambdaDef(params, predicate, expression):
                self.symbol_table.add_scope(ScopeContext.LAMBDA)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)

                self._populate_loop_parameters(params)
                _param_symbols = self._convert_identifier_to_symbol(params)

                self.symbol_table.pop_scope_level()
                return ast_.LambdaDef(_param_symbols, _predicate, _expression), False

            # Symbols
            # TODO check for enum def in all assignment statements
            case ast_.Assignment(ast_.Identifier(name), _):
                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.VARIABLE,
                )
            case ast_.Assignment(ast_.TypedName(ast_.Identifier(name), declared_type), _):
                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.VARIABLE,
                    _ast_to_type(self.symbol_table, declared_type),
                )
            case ast_.RecordDef(ast_.Identifier(name), items):
                fields: dict[str, BaseType] = OrderedDict()
                for item in items:
                    if not isinstance(item.name, ast_.Identifier):
                        raise SimileTypeError(f"Invalid struct field name (must be an identifier): {item.name}", item)
                    fields[item.name.name] = _ast_to_type(self.symbol_table, item.type_)

                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.RECORD,
                    RecordType(fields=fields),
                )
                _symbol = self._convert_identifier_to_symbol(ast_.Identifier(name))
                return ast_.RecordSymbol(_symbol), False
            case ast_.Import(module_file_path, import_objects):
                raise NotImplementedError("Import statements are not yet supported in the symbol table population pass")
                _populate_from_import(self.symbol_table, import_objects, module_file_path)

            # By this point, all identifiers should have been added to the symbol table
            # Replace them with symbol ids corresponding to the symbol table entry
            case ast_.Identifier(_) | ast_.MapletIdentifier(_) | ast_.TupleIdentifier(_):
                return self._convert_identifier_to_symbol(ast), False
        return None, True

    def _convert_identifier_to_symbol(self, ast: ast_.IdentifierListTypes) -> ast_.SymbolListTypes:
        match ast:
            case ast_.Identifier(name):
                symbol_table_entry = self.symbol_table.lookup_identifier_in_current_scope(name)
                return ast_.Symbol(symbol_table_entry.id_, symbol_table_entry)
            case ast_.MapletIdentifier((left, right)):
                _left = self._convert_identifier_to_symbol(left)
                _right = self._convert_identifier_to_symbol(right)
                return ast_.MapletSymbol(_left, _right)
            case ast_.TupleIdentifier(identifiers):
                _identifiers = [self._convert_identifier_to_symbol(ident) for ident in identifiers]
                return ast_.TupleSymbol(tuple(_identifiers))
        raise ValueError(f"Unsupported identifier type: {type(ast)}. This should not happen")

    def _populate_loop_parameters(self, iterable_names: ast_.IdentifierListTypes) -> None:
        if isinstance(iterable_names, ast_.Identifier):
            self.symbol_table.add_symbol(
                iterable_names.name,
                IdentifierContext.LOOP_VARIABLE,
            )
        elif isinstance(iterable_names, ast_.TupleIdentifier):
            for ident in iterable_names.flatten():
                self._populate_loop_parameters(ident)
        else:
            raise SimileTypeError(f"Invalid for loop variable name (must be an identifier, maplet identifier, or tuple identifier): {iterable_names}", iterable_names)

    def _find_unbound_identifiers(self, ast: ast_.Quantifier) -> ast_.TupleIdentifier:
        """Finds unbound identifiers in an unqualified quantifier."""
        possible_generators = list(filter(lambda x: x.op_type == ast_.BinaryOperator.IN, ast.predicate.find_all_instances(ast_.BinaryOp)))
        possible_bound_identifiers: list[ast_.IdentifierListTypes] = []
        possible_bound_identifier_names: set[ast_.Identifier] = set()
        for possible_generator in possible_generators:
            if isinstance(possible_generator.left, ast_.IdentifierListTypes):
                possible_bound_identifiers.append(possible_generator.left)
                possible_bound_identifier_names.update(possible_generator.left.flatten())

            if isinstance(possible_generator.left, ast_.BinaryOp):
                left = possible_generator.left.try_cast_maplet_to_maplet_identifier()
                if left is None:
                    continue

                possible_bound_identifiers.append(left)
                possible_bound_identifier_names.update(left.flatten())

        for possible_bound_identifier in possible_bound_identifier_names:
            if not self.symbol_table.does_symbol_exist_in_current_scope(possible_bound_identifier.name):
                possible_bound_identifiers = list(filter(lambda x: not x.contains(possible_bound_identifier), possible_bound_identifiers))

        if not possible_bound_identifiers:
            raise SimileTypeError(
                f"Failed to infer bound variables for quantifier {ast_.ast_to_source(ast)}. "
                "Either the expression is ambiguously overwriting a predefined variable in scope, "
                "or no valid generators are present in the quantification expression. Please explicitly state bound variables",
                ast,
            )

        return ast_.TupleIdentifier(tuple(possible_bound_identifiers))


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
