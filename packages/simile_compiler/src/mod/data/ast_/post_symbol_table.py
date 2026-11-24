"""Parser-only AST nodes. These do not hold types or other analysis information.
These types will be replaced by typed ASTs will be used after type analysis"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar, overload, TYPE_CHECKING

from src.mod.data.ast_.base import ASTNode
from src.mod.data.helpers.dataclass import flatten
from src.mod.data.symbol_table.entry import SymbolTableIdentifierEntry

if TYPE_CHECKING:
    from src.mod.data.types.base import BaseType
    from src.mod.data.ast_.common import Statements, True_


@dataclass
class Symbol(ASTNode):
    """Symbol-table converted identifier for variables, functions, etc. in the AST."""

    symbol_table_entry: SymbolTableIdentifierEntry

    def flatten(self) -> list[Symbol]:
        """Used to simplify the flatten operation of :cls:`MapletSymbol` and :cls:`TupleSymbol`"""
        return [self]


type TupleSymbolItem = Symbol | TupleSymbol


@dataclass
class TupleSymbol(ASTNode):
    """Special variation of tuple used for binding loop and quantification variables"""

    items: tuple[TupleSymbolItem, ...]

    def flatten(self) -> list[Symbol]:
        """Used to simplify the flatten operation of :cls:`MapletSymbol` and :cls:`TupleSymbol`"""
        return flatten(list(map(lambda item: item.flatten(), self.items)))


@dataclass
class MapletSymbol(TupleSymbol):
    """Special variation of maplet used for binding loop and quantification variables"""

    @overload
    def __init__(self, left: tuple[TupleSymbolItem, TupleSymbolItem]) -> None: ...

    @overload
    def __init__(self, left: TupleSymbolItem, right: TupleSymbolItem) -> None: ...

    def __init__(
        self,
        left: TupleSymbolItem | tuple[TupleSymbolItem, TupleSymbolItem],
        right: TupleSymbolItem | None = None,
    ) -> None:
        super().__init__(())
        if isinstance(left, tuple):
            assert right is None, "If left is a tuple, right must be None"
            self.items = left
        else:
            assert right is not None, "If left is not a tuple, right must not be None"
            self.items = (left, right)

    @property
    def left(self) -> TupleSymbolItem:
        return self.items[0]

    @left.setter
    def left(self, value: TupleSymbolItem) -> None:
        self.items = (value, self.items[1])

    @property
    def right(self) -> TupleSymbolItem:
        return self.items[1]

    @right.setter
    def right(self, value: TupleSymbolItem) -> None:
        self.items = (self.items[0], value)


SymbolListTypes = Symbol | TupleSymbol | MapletSymbol


@dataclass
class RecordDefSymbol(ASTNode):
    name: Symbol
    fields: dict[str, BaseType]


@dataclass
class ProcedureDefSymbol(ASTNode):
    name: Symbol
    args: list[Symbol]
    body: ASTNode | Statements


@dataclass
class LambdaDefSymbol(ASTNode):
    params: list[Symbol]
    predicate: ASTNode | True_
    expression: ASTNode


# Experimenting with a generic-typed version of symbolic tuple. Dont anticipate this becoming that useful tho

# IdentifierOrSymbol = TypeVar("IdentifierOrSymbol", Identifier, Symbol)
# SymbolicTupleItem: TypeAlias = IdentifierOrSymbol | "SymbolicTuple[IdentifierOrSymbol]"


# @dataclass
# class SymbolicTuple(ASTNode, Generic[IdentifierOrSymbol]):
#     """Special variation of tuple used for binding loop and quantification variables"""

#     items: tuple[SymbolicTupleItem[IdentifierOrSymbol], ...]

#     def flatten(self) -> list[IdentifierOrSymbol]:
#         return flatten(list(map(lambda item: item.flatten(), self.items)))


# @dataclass
# class SymbolicMaplet(SymbolicTuple[IdentifierOrSymbol], Generic[IdentifierOrSymbol]):
#     """Special variation of maplet used for binding loop and quantification variables"""

#     @overload
#     def __init__(self, left: tuple[SymbolicTupleItem[IdentifierOrSymbol], SymbolicTupleItem[IdentifierOrSymbol]]) -> None: ...

#     @overload
#     def __init__(self, left: SymbolicTupleItem[IdentifierOrSymbol], right: SymbolicTupleItem[IdentifierOrSymbol]) -> None: ...

#     def __init__(
#         self,
#         left: SymbolicTupleItem[IdentifierOrSymbol] | tuple[SymbolicTupleItem[IdentifierOrSymbol], SymbolicTupleItem[IdentifierOrSymbol]],
#         right: SymbolicTupleItem[IdentifierOrSymbol] | None = None,
#     ) -> None:
#         super().__init__(())
#         if isinstance(left, tuple):
#             assert right is None, "If left is a tuple, right must be None"
#             self.items = left
#         else:
#             assert right is not None, "If left is not a tuple, right must not be None"
#             self.items = (left, right)

#     @property
#     def left(self) -> SymbolicTupleItem[IdentifierOrSymbol]:
#         return self.items[0]

#     @left.setter
#     def left(self, value: SymbolicTupleItem[IdentifierOrSymbol]) -> None:
#         self.items = (value, self.items[1])

#     @property
#     def right(self) -> SymbolicTupleItem[IdentifierOrSymbol]:
#         return self.items[1]

#     @right.setter
#     def right(self, value: SymbolicTupleItem[IdentifierOrSymbol]) -> None:
#         self.items = (self.items[0], value)
