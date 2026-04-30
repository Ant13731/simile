"""Parser-only AST nodes. These do not hold types or other analysis information.
These types will be replaced by typed ASTs will be used after type analysis"""

from dataclasses import dataclass
from typing import Generic, TypeVar

from src.mod.data.ast_.base import ASTNode
from src.mod.data.symbol_table.entry import SymbolTableIdentifierEntry


@dataclass
class Symbol(ASTNode):
    """Symbol-table converted identifier for variables, functions, etc. in the AST."""

    id: int
    symbol_table_entry: SymbolTableIdentifierEntry


@dataclass
class TupleSymbol(ASTNode):
    """Special variation of tuple used for binding loop and quantification variables"""

    items: tuple[SymbolListTypes, ...]


L = TypeVar("L", bound="Symbol | TupleSymbol | MapletSymbol")
R = TypeVar("R", bound="Symbol | TupleSymbol | MapletSymbol")


@dataclass
class MapletSymbol(TupleSymbol, Generic[L, R]):
    """Special variation of maplet used for binding loop and quantification variables"""

    def __init__(self, left: L | tuple[SymbolListTypes], right: R | None = None) -> None:
        if isinstance(left, tuple):
            assert right is None, "If left is a tuple, right must be None"
            super().__init__(left)
        else:
            assert right is not None, "If left is not a tuple, right must be provided"
            super().__init__((left, right))

    @property
    def left(self) -> L:
        # python cant handle generic tuples just yet, so just ignore the type checker here
        return self.items[0]  # type: ignore

    @left.setter
    def left(self, value: L) -> None:
        self.items = (value, self.items[1])

    @property
    def right(self) -> R:
        return self.items[1]  # type: ignore

    @right.setter
    def right(self, value: R) -> None:
        self.items = (self.items[0], value)


SymbolListTypes = Symbol | TupleSymbol | MapletSymbol
