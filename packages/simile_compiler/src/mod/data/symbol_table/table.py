from dataclasses import dataclass, field
from enum import Enum, auto

from src.mod.data.types.base import BaseType
from src.mod.data.types.meta import ModuleImports, ImportedSymbol
from src.mod.data.symbol_table.entry import (
    IdentifierContext,
    ScopeContext,
    SymbolTableIdentifierEntry,
    ScopeTableEntry,
)
from src.mod.data.symbol_table.error import SymbolTableError


@dataclass
class SymbolTable:
    symbols: dict[int, SymbolTableIdentifierEntry] = field(default_factory=dict)
    scopes: dict[int, ScopeTableEntry] = field(default_factory=dict)

    _symbol_id_counter: int = 0
    _scope_id_counter: int = 0
    _current_scope_list: list[ScopeTableEntry] = field(default_factory=list)

    def add_symbol(self, name: str, context: IdentifierContext, declared_type: BaseType) -> SymbolTableIdentifierEntry:
        """Returns the new symbol table entry."""
        current_scope = self.current_scope()
        maybe_existing_symbol = self.get_symbol_by_name_in_current_scope(name)
        if maybe_existing_symbol is not None:
            raise SymbolTableError(
                f"Cannot add new symbol with name {name} to ID {(self._symbol_id_counter+1, current_scope.id_)} because a symbol with that name already exists in the current scope: {maybe_existing_symbol}"
            )

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
        return new_symbol

    def add_scope(self, context: ScopeContext) -> ScopeTableEntry:
        """Returns the new scope table entry."""
        self._scope_id_counter += 1
        new_scope = ScopeTableEntry(
            id_=self._scope_id_counter,
            parent=self._current_scope_list[-1].id_ if self._current_scope_list else None,
            declared_symbols=set(),
            context=context,
        )

        self.scopes[new_scope.id_] = new_scope
        self._current_scope_list.append(new_scope)
        return new_scope

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

    def current_scope(self) -> ScopeTableEntry:
        """Returns the current scope table entry."""
        if not self._current_scope_list:
            raise SymbolTableError("Cannot get current scope because no scope has been added to the symbol table yet (current_scope_list is empty)")
        return self._current_scope_list[-1]

    def lookup_identifier(self, identifier: str) -> SymbolTableIdentifierEntry:
        """Looks up a symbol by its id and scope, returning the symbol table entry."""
        for scope in reversed(self._current_scope_list):
            for symbol_id in scope.declared_symbols:
                if self.symbols[symbol_id].name == identifier:
                    return self.symbols[symbol_id]
        raise SymbolTableError(f"Identifier '{identifier}' not found in current scope")

    def symbol_exists_in_current_scope(self, name: str) -> bool:
        return self.get_symbol_by_name_in_current_scope(name) is not None

    def get_symbol_by_name_in_current_scope(self, name: str) -> SymbolTableIdentifierEntry | None:
        for symbol_id in self.current_scope().declared_symbols:
            if self.symbols[symbol_id].name == name:
                return self.symbols[symbol_id]
        return None

    def get_top_level_symbols(self) -> list[SymbolTableIdentifierEntry]:
        """Returns a list of symbol table entries for symbols declared at the top level (i.e. in the base scope)."""
        top_level_scopes = [scope for scope in self.scopes.values() if scope.parent is None]
        if not top_level_scopes:
            raise SymbolTableError("No top level scope found in symbol table")
        if len(top_level_scopes) > 1:
            raise SymbolTableError(f"Multiple top level scopes found in symbol table. This should be impossible. Scope ids: {[scope.id_ for scope in top_level_scopes]}")
        top_level_scope = top_level_scopes[0]
        return [self.symbols[symbol_id] for symbol_id in top_level_scope.declared_symbols]

    def debug(self) -> str:
        ret = "Symbol Table:\n"
        ret += f"  Symbol counter: {self._symbol_id_counter}\n"
        ret += f"  Scope counter: {self._scope_id_counter}\n"
        ret += "  Current Scope List:\n"
        for scope_entry in self._current_scope_list:
            ret += f"    ScopeID: {scope_entry.id_} | Parent: {scope_entry.parent} | Context: {scope_entry.context} | Symbols: {scope_entry.declared_symbols}\n"
        ret += "  All Scopes:\n"
        for scope_id, scope_entry in self.scopes.items():
            ret += f"    ScopeID: {scope_id} | Parent: {scope_entry.parent} | Context: {scope_entry.context} | Symbols: {scope_entry.declared_symbols}\n"
        ret += "  Symbols:\n"
        for symbol_id, symbol_entry in self.symbols.items():
            ret += f"    SymbID: {symbol_id} | ScopeID: {symbol_entry.scope} | Name: {symbol_entry.name} | Context: {symbol_entry.context} | Type: {symbol_entry.declared_type}\n"

        return ret
