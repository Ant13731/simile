from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
from typing import TypeVar

from src.mod.data import ast_
from src.mod.pipeline.analysis.normalize_ast import normalize_ast
from src.mod.pipeline.analysis.populate_symbol_table import populate_symbol_table
from src.mod.pipeline.analysis.reserved_keywords import reserved_keywords_check
from src.mod.pipeline.analysis.ambiguous_quantification import promote_quantifiers_to_qualified
from src.mod.pipeline.analysis.type_analysis import type_check


def semantic_analysis(ast: ast_.ASTNode) -> ast_.ASTNode:
    """Combines all semantic analysis passes into one function:
    - Populates AST environments
    - Checks for reserved keywords
    - Infers bound identifiers for quantifiers
    - Performs type checking
    """
    reserved_keywords_check(ast)
    symbol_table = populate_symbol_table(ast)
    ast = promote_quantifiers_to_qualified(ast)
    ast = normalize_ast(ast)
    type_check(ast)
    return ast
