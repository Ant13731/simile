from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
import pathlib
from typing import TypeVar
from warnings import deprecated

from src.mod.pipeline.scanner import Location, KEYWORD_TABLE
from src.mod.pipeline.parser import parse, ParseError
from src.mod.data import ast_
from src.mod.data.symbol_table import SymbolTable
from src.mod.data.types import BaseType, SimileTypeError
from src.mod.data.ast_.symbol_table_types import (
    SimileType,
    ModuleImports,
    ProcedureTypeDef,
    StructTypeDef,
    EnumTypeDef,
    # SimileTypeError,
    BaseSimileType,
)


@deprecated("No longer using environments")
def populate_bound_identifiers(ast: ast_.ASTNode) -> None:
    """Attempts to infer the bound variables of implicitly-bound quantifiers"""
    if isinstance(ast, ast_.Quantifier) and ast._bound_identifiers == set():
        possible_generators = list(filter(lambda x: x.op_type == ast_.BinaryOperator.IN, ast.predicate.find_all_instances(ast_.BinaryOp)))
        possible_bound_identifiers: list[ast_.Identifier | ast_.MapletIdentifier] = []
        possible_bound_identifier_names: set[ast_.Identifier] = set()
        for possible_generator in possible_generators:
            if isinstance(possible_generator.left, ast_.Identifier | ast_.MapletIdentifier):
                possible_bound_identifiers.append(possible_generator.left)
                possible_bound_identifier_names.update(possible_generator.left.flatten())

            if isinstance(possible_generator.left, ast_.BinaryOp):
                left = possible_generator.left.try_cast_maplet_to_maplet_identifier()
                if left is None:
                    continue

                possible_bound_identifiers.append(left)
                possible_bound_identifier_names.update(left.flatten())

        for possible_bound_identifier in possible_bound_identifier_names:
            assert ast._env is not None
            if ast._env.get(possible_bound_identifier.name) is not None:
                possible_bound_identifiers = list(filter(lambda x: not x.contains(possible_bound_identifier), possible_bound_identifiers))

        if not possible_bound_identifiers:
            raise SimileTypeError(
                f"Failed to infer bound variables for quantifier {ast_.ast_to_source(ast)}. "
                "Either the expression is ambiguously overwriting a predefined variable in scope, "
                "or no valid generators are present in the quantification expression. Please explicitly state bound variables",
                ast,
            )

        ast._bound_identifiers = set(possible_bound_identifiers)

    for child in ast.children(True):
        populate_bound_identifiers(child)


def find_unbound_identifiers(symbol_table: SymbolTable, ast: ast_.Quantifier) -> ast_.TupleIdentifier:
    """Makes a new QualifiedQuantifier from a Quantifier, slotting in the bound identifiers from the symbol table."""
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
        if not symbol_table.does_symbol_exist_in_current_scope(possible_bound_identifier.name):
            possible_bound_identifiers = list(filter(lambda x: not x.contains(possible_bound_identifier), possible_bound_identifiers))

    if not possible_bound_identifiers:
        raise SimileTypeError(
            f"Failed to infer bound variables for quantifier {ast_.ast_to_source(ast)}. "
            "Either the expression is ambiguously overwriting a predefined variable in scope, "
            "or no valid generators are present in the quantification expression. Please explicitly state bound variables",
            ast,
        )

    quantifier_bound_identifiers = ast_.TupleIdentifier(tuple(possible_bound_identifiers))

    # Needed to promote quantifier to qualified quantifier later on - hide data in the node for now
    # Populated during symbol table creation
    ast._temp_bound_identifiers_before_qualified_promotion = quantifier_bound_identifiers

    return quantifier_bound_identifiers


def promote_quantifiers_to_qualified(ast: ast_.ASTNode) -> ast_.ASTNode:
    """MUST BE RUN AFTER POPULATING THE SYMBOL TABLE ENVIRONMENTS

    Symbol table population has a side effect on Quantifiers!!"""
    return ast.find_and_replace_with_func(_promote_quantifiers_to_qualified_aux)


def _promote_quantifiers_to_qualified_aux(ast: ast_.ASTNode) -> ast_.ASTNode | None:
    if not isinstance(ast, ast_.Quantifier):
        return None

    if ast._temp_bound_identifiers_before_qualified_promotion is None:
        raise SimileTypeError("Cannot promote quantifier to qualified quantifier because bound identifiers have not been found", ast)

    bound_identifiers = ast._temp_bound_identifiers_before_qualified_promotion
    return ast_.QualifiedQuantifier(bound_identifiers, ast.predicate, ast.expression, ast.op_type)
