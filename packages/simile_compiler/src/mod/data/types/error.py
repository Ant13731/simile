from typing import TYPE_CHECKING, Callable
from functools import wraps

if TYPE_CHECKING:
    from src.mod.data.ast_.base import ASTNode
    from src.mod.data.types import BaseType


class SimileTypeError(Exception):
    """Custom exception for Simile type errors."""

    def __init__(self, message: str, node: ASTNode | None = None) -> None:
        message = f"SimileTypeError: {message}"
        self.node = node
        super().__init__(message)
        if node is not None:
            self.add_ast(node)

    def add_ast(self, node: ASTNode):
        """Add an AST node to the error message."""
        from src.mod.pipeline.printers.ast_ import ast_to_source

        self.node = node
        self.add_note(f"Error at node {node.get_location()}: {ast_to_source(node)}")

    @classmethod
    def wrap_type_check_error_with_ast[T](cls, func: Callable[[T, ASTNode], BaseType]) -> Callable[[T, ASTNode], BaseType]:
        @wraps(func)
        def wrapper(self, ast: ASTNode) -> BaseType:
            try:
                return func(self, ast)
            except SimileTypeError as e:
                e.add_ast(ast)
                raise e

        return wrapper
