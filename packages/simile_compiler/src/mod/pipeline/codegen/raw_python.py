from dataclasses import dataclass
from functools import singledispatchmethod

from src.mod.data import ast_, types, traits
from src.mod.data.symbol_table import SymbolTable
from src.mod.pipeline.analysis import SemanticAnalysis


@dataclass
class RawSimileToPythonCodegen:
    symbol_table: SymbolTable

    def lower(self, ast: ast_.ASTNode) -> str:
        return self._lower(ast, 0)

    @singledispatchmethod
    def _lower(self, ast: ast_.ASTNode, indent: int) -> str:
        raise NotImplementedError(f"Lowering not implemented for {type(ast)}")

    def _(self, ast)