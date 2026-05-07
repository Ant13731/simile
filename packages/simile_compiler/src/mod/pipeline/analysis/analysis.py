from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
from typing import TypeVar

from src.mod.data import ast_
from src.mod.pipeline.analysis.normalize_ast import assert_no_parser_only_nodes, normalize_ast
from src.mod.pipeline.analysis.populate_symbol_table import populate_symbol_table
from src.mod.pipeline.analysis.reserved_keywords import reserved_keywords_check
from src.mod.pipeline.analysis.type_analysis import resolve_type


def semantic_analysis(ast: ast_.ASTNode) -> ast_.ASTNode:
    """Combines all semantic analysis passes into one function:
    - Populates AST environments
    - Checks for reserved keywords
    - Infers bound identifiers for quantifiers
    - Performs type checking
    """
    reserved_keywords_check(ast)
    symbol_table = populate_symbol_table(ast)
    ast = normalize_ast(ast)
    assert_no_parser_only_nodes(ast)
    # TODO:
    # rewrite type check
    #  - make it so that we can determine the type of any ASTNode (using the symbol table for deferred type lookups)
    #  - make sure the values of types match their declarations
    #  - move get_type out into a standalone function
    # well-definedness check? anything else needed?
    resolve_deferred_symbol_table_types(symbol_table)
    type_check(ast, symbol_table)
    return ast
