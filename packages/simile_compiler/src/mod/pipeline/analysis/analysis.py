from __future__ import annotations
from dataclasses import dataclass

from src.mod.data import ast_
from src.mod.data.symbol_table import SymbolTable
from src.mod.pipeline.analysis.normalize_ast import assert_no_parser_only_nodes, normalize_ast
from src.mod.pipeline.analysis.populate_symbol_table import make_symbol_table
from src.mod.pipeline.analysis.reserved_keywords import reserved_keywords_check
from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer


def semantic_analysis(ast: ast_.ASTNode, no_standard_library: bool = False) -> SemanticAnalysis:
    """Combines all semantic analysis passes into one function"""

    reserved_keywords_check(ast)
    ast = normalize_ast(ast)
    symbol_table = make_symbol_table(ast, no_standard_library)
    assert_no_parser_only_nodes(ast)
    type_synthesizer = TypeSynthesizer(symbol_table)
    type_synthesizer.type_check(ast)
    # TODO well-definedness check
    return SemanticAnalysis(ast, symbol_table, type_synthesizer)


@dataclass
class SemanticAnalysis:
    ast: ast_.ASTNode
    symbol_table: SymbolTable
    type_synthesizer: TypeSynthesizer
