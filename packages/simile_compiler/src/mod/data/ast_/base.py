from __future__ import annotations
from dataclasses import dataclass, fields, field
from typing import Generator, Any, Generic, TypeVar, Callable
from functools import wraps
from warnings import deprecated

from src.mod.pipeline.scanner import Location
from src.mod.data.ast_.operators import Operators
from src.mod.data.ast_.helpers.dataclass import dataclass_traverse, dataclass_find_and_replace
from src.mod.data.ast_.symbol_table_types import SimileType, DeferToSymbolTable, SimileTypeError, PairType, TupleType
from src.mod.data.ast_.symbol_table_env import SymbolTableEnvironment

T = TypeVar("T")


@dataclass
class ASTNode:
    """Base class for all AST nodes."""

    def __post_init__(self) -> None:
        self._env: SymbolTableEnvironment | None = None
        self._start_location: Location | None = None
        self._end_location: Location | None = None
        self._file_location: str | None = None

    @deprecated("Well-formedness checks are being moved to a separate analysis pass")
    def well_formed(self) -> bool:
        """Check if the variables in expressions are well-formed (i.e., no clashes between :attr:`bound` and :attr:`free` variables)."""
        return True

    @deprecated("Well-formedness checks are being moved to a separate analysis pass")
    @property
    def bound(self) -> set:
        """Returns the set of bound variables in the AST node."""
        return set()

    @deprecated("Well-formedness checks are being moved to a separate analysis pass")
    @property
    def free(self) -> set:
        """Returns the set of free variables in the AST node."""
        return set()

    @deprecated("Moving to trait-based external type system")
    @property
    def get_type(self) -> SimileType:
        """Returns the type of the AST node.

        Initially, :cls:`Identifier` nodes will return a :cls:`DeferToSymbolTable` type.
        After running :func:`src.mod.analysis.type_analysis.populate_ast_with_types`, all nodes will contain resolved types.
        """
        if self._env is None:
            raise SimileTypeError("Type analysis must be run before calling the `get_type` function (self._env is None)", self)
        return self._get_type()

    @deprecated("Moving to trait-based external type system")
    def _get_type(self) -> SimileType:
        """"""
        raise NotImplementedError

    def contains_by_type(self, node_type: type[ASTNode], also_has_op_type: Operators | None = None) -> bool:
        """Check if the AST node contains a specific type of node.

        If also_has_op_type is provided, only counts nodes of the specified type that also have an op_type field matching also_has_op_type."""

        def is_matching_node(n: Any) -> bool:
            if not isinstance(n, node_type):
                return False
            if also_has_op_type is None:
                return True
            if not hasattr(n, "op_type"):
                return False
            assert hasattr(n, "op_type")
            return n.op_type == also_has_op_type  # type: ignore

        return any(dataclass_traverse(self, is_matching_node))

    def contains(self, item: ASTNode | Any) -> bool:
        """Check if the AST node contains a specific item."""
        return any(dataclass_traverse(self, lambda n: n == item))

    def find_all_instances(self, type_: type[T], with_op_type: Operators | None = None) -> list[T]:
        """Returns a flattened list of all instances of a specific type in the AST.

        Most useful for finding identifiers nested within expressions.
        """

        def isinstance_with_op_type(n: Any) -> T | None:
            if not isinstance(n, type_):
                return None
            if with_op_type is None:
                return n
            if hasattr(n, "op_type") and n.op_type == with_op_type:  # type: ignore
                return n
            return None

        return list(filter(None, dataclass_traverse(self, isinstance_with_op_type)))

    def children(self, ast_nodes_only: bool = False) -> Generator[ASTNode | Any, None, None]:
        """Returns a list of all children AST nodes (only 1 level deep). Includes op_type fields if they exist."""
        for f in fields(self):
            field_value = getattr(self, f.name)
            if isinstance(field_value, list):
                for item in field_value:
                    yield item
            else:
                if isinstance(field_value, ASTNode):
                    yield field_value
                elif not ast_nodes_only:
                    # If we are not filtering for ASTNodes only, yield the field value directly
                    yield field_value

    def find_and_replace(self, find: ASTNode | Any, replace: ASTNode | Any) -> ASTNode:
        """Find and replace AST nodes using a syntactic substitution."""

        def rewrite_func(node: ASTNode | Any) -> ASTNode | None:
            if node == find:
                return replace
            return None

        return dataclass_find_and_replace(self, rewrite_func)

    def find_and_replace_with_func(self, rewrite_func: Callable[[ASTNode | Any], ASTNode | None]) -> ASTNode:
        """Find and replace AST nodes using a rewrite function.

        The rewrite function should return the new AST node or None if no replacement is needed.
        """

        return dataclass_find_and_replace(self, rewrite_func)

    def is_leaf(self) -> bool:
        """Check if the AST node is a leaf node (i.e., has no dataclass/list of dataclass children)."""
        for f in fields(self):
            field_value = getattr(self, f.name)
            if isinstance(field_value, list):
                if any(isinstance(item, ASTNode) for item in field_value):
                    return False
            elif isinstance(field_value, ASTNode):
                return False
        return True

    def add_location(self, start: Location, end: Location, file: str) -> None:
        self._start_location = start
        self._end_location = end
        self._file_location = file

    def get_location(self) -> str:
        return f"({self._file_location}:{self._start_location}:{self._end_location})"
