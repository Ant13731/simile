from dataclasses import dataclass, field
from enum import Enum, auto

from src.mod.data.types.base import BaseType


class SymbolTableError(Exception):
    pass


class IdentifierContext(Enum):
    VARIABLE = auto()
    RECORD = auto()
    RECORD_FIELD = auto()
    PROCEDURE = auto()
    PROCEDURE_PARAMETER = auto()
    QUANTIFICATION_VARIABLE = auto()
    LOOP_VARIABLE = auto()
    LAMBDA_VARIABLE = auto()


@dataclass
class SymbolTableIdentifierEntry:
    id_: int
    scope: int
    name: str
    declared_type: BaseType | None

    """How was this symbol table entry (identifier) declared? Ex. as a variable or as the name of a procedure?"""
    context: IdentifierContext


class ScopeContext(Enum):
    BASE = auto()
    RECORD = auto()
    PROCEDURE = auto()
    QUANTIFICATION = auto()
    LOOP = auto()
    LAMBDA = auto()


@dataclass
class ScopeTableEntry:
    id_: int
    parent: int | None

    """Symbols in this scope"""
    declared_symbols: set[int]

    """Why was a new scope created? Ex. for a procedure body or a for loop body"""
    context: ScopeContext


@dataclass
class SymbolTable:
    symbols: dict[int, SymbolTableIdentifierEntry]
    scopes: dict[int, ScopeTableEntry]

    _symbol_id_counter: int = 0
    _scope_id_counter: int = 0
    _current_scope_list: list[ScopeTableEntry] = field(default_factory=list)

    def add_symbol(self, name: str, context: IdentifierContext, declared_type: BaseType | None = None) -> int:
        """Returns the id of the new symbol table entry."""
        if len(self._current_scope_list) == 0:
            raise SymbolTableError("Cannot add symbol because no scope has been added to the symbol table yet (current_scope_list is empty)")
        current_scope = self._current_scope_list[-1]

        if name in [self.symbols[symbol_id].name for symbol_id in current_scope.declared_symbols]:
            raise SymbolTableError(f"Cannot add new symbol with name {name} because a symbol with that name already exists in the current scope with id {current_scope.id_}")

        self._symbol_id_counter += 1
        new_symbol = SymbolTableIdentifierEntry(
            id_=self._symbol_id_counter,
            scope=current_scope.id_,
            name=name,
            context=context,
            declared_type=declared_type,
        )

        self.symbols[new_symbol.id_] = new_symbol
        current_scope.declared_symbols.add(new_symbol.id_)
        return self._symbol_id_counter

    def add_scope(self, context: ScopeContext) -> int:
        """Returns the id of the new scope table entry."""
        self._scope_id_counter += 1
        new_scope = ScopeTableEntry(
            id_=self._scope_id_counter,
            parent=self._current_scope_list[-1].id_ if self._current_scope_list else None,
            declared_symbols=set(),
            context=context,
        )

        self.scopes[new_scope.id_] = new_scope
        self._current_scope_list.append(new_scope)
        return self._scope_id_counter

    def pop_scope_level(self) -> None:
        """Pops the current scope level, changing the current scope for new additions."""
        if not self._current_scope_list:
            raise SymbolTableError("Cannot pop scope level because already at top level")
        self._current_scope_list.pop()

    def lookup_symbol(self, symbol_id: int, scope_id: int) -> SymbolTableIdentifierEntry:
        """Looks up a symbol by its id and scope, returning the symbol table entry."""
        if symbol_id not in self.symbols:
            raise SymbolTableError(f"Symbol with id {symbol_id} not found in symbol table")
        if scope_id not in self.scopes:
            raise SymbolTableError(f"Scope with id {scope_id} not found in symbol table")
        if symbol_id not in self.scopes[scope_id].declared_symbols:
            raise SymbolTableError(f"Symbol with id {symbol_id} not declared in scope with id {scope_id}")
        return self.symbols[symbol_id]
