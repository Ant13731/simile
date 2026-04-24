from __future__ import annotations
from functools import singledispatchmethod
from dataclasses import dataclass, field
from typing import ClassVar, Any, Generic, TypeVar
import sys

from src.mod.data import ast_

T = TypeVar("T")


class CodeGeneratorError(Exception):
    """Custom exception for code generation errors."""

    pass


@dataclass
class CodeGenerator:
    ast: ast_.ASTNode

    def hash_variable_name(self, name: str) -> str:
        """Hash the variable name to ensure it is unique in the generated code."""
        return f"_fresh_var_{hash(name) + sys.maxsize + 1}"

    def generate(self) -> Any:
        if self.ast._env is None:
            raise ValueError("AST environment should have been populated before code generation (see analysis module).")

        return self._generate_code(self.ast)

    def build(self, target_folder_path: str = "packages/simile_compiler/build") -> None:
        raise NotImplementedError("Build method is not implemented. This should be overridden in subclasses.")

    @singledispatchmethod
    def _generate_code(self, ast: ast_.ASTNode) -> Any:
        """Auxiliary function for generating LLVM code based on the type of AST node. See :func:`generate_llvm_code`."""
        raise NotImplementedError(f"Code generation not implemented for node type: {type(ast)} with value {ast}")
