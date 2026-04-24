from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
from typing import TypeVar

from src.mod.data import ast_
from src.mod.pipeline.analysis.populate_ast_environments import populate_ast_environments
from src.mod.pipeline.analysis.reserved_keywords import reserved_keywords_check
from src.mod.pipeline.analysis.ambiguous_quantification import populate_bound_identifiers
from src.mod.pipeline.analysis.type_analysis import type_check


T = TypeVar("T", bound=ast_.ASTNode)


def semantic_analysis(ast: T) -> T:
    """Combines all semantic analysis passes into one function:
    - Populates AST environments
    - Checks for reserved keywords
    - Infers bound identifiers for quantifiers
    - Performs type checking
    """
    ast = populate_ast_environments(ast)
    ast = reserved_keywords_check(ast)
    populate_bound_identifiers(ast)
    type_check(ast)
    return ast
