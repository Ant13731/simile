from functools import singledispatchmethod
from dataclasses import dataclass, field
from loguru import logger

from src.mod.data import ast_


@dataclass
class StructureMatcher:
    match_identifier_names: set[str]

    _matched_so_far: dict[str, ast_.ASTNode] = field(default_factory=lambda: {})

    def match(self, ast: ast_.ASTNode, against: ast_.ASTNode) -> dict[str, ast_.ASTNode] | None:
        # NOTE: params are swapped to work with single dispatch method
        if self._match(against, ast):
            return self._matched_so_far
        return None

    @singledispatchmethod
    def _match(self, against: ast_.ASTFieldChildren, ast: ast_.ASTFieldChildren) -> bool:
        raise NotImplementedError(f"Structural match not implemented for {type(ast)}. Attempted matching {ast} against {against}. Matched so far: {self._matched_so_far}")

    @_match.register
    def _(self, against: ast_.Identifier, ast: ast_.ASTFieldChildren) -> bool:
        from src.mod.pipeline.printer.ast_ import ast_to_source

        if not isinstance(ast, ast_.ASTNode):
            return False
        logger.debug(f"Matching against identifier: {against.name} with AST: {ast_to_source(ast)}")
        if against.name not in self.match_identifier_names:
            return False
        if against.name not in self._matched_so_far:
            self._matched_so_far[against.name] = ast
            logger.debug(f"Matched identifier: {against.name} to AST: {ast_to_source(ast)}")

        return self._matched_so_far[against.name] == ast

    @_match.register
    def _(self, against: ast_.ASTNode, ast: ast_.ASTFieldChildren) -> bool:
        from src.mod.pipeline.printer.ast_ import ast_to_source

        if not isinstance(ast, ast_.ASTNode):
            return False
        logger.debug(f"Matching against ASTNode: {ast_to_source(against)} with AST: {ast_to_source(ast)}")
        # Use a purely structural match, but at least one side must be a subclass or eq to the other
        if not issubclass(type(against), type(ast)) and not issubclass(type(ast), type(against)):
            return False
        if len(list(against.children())) != len(list(ast.children())):
            return False
        for against_child, ast_child in zip(against.children(), ast.children()):
            if not self._match(against_child, ast_child):
                return False
        return True

    @_match.register
    def _(self, against: list, ast: ast_.ASTFieldChildren) -> bool:
        from src.mod.pipeline.printer.ast_ import ast_to_source

        if not isinstance(ast, list):
            return False
        logger.debug(f"Matching against list: {against} with AST: {list(map(ast_to_source, ast))}")
        if len(against) != len(ast):
            return False
        for against_item, ast_item in zip(against, ast):
            if not self._match(against_item, ast_item):
                return False
        return True

    @_match.register
    def _(self, against: ast_.Operators, ast: ast_.ASTFieldChildren) -> bool:
        if isinstance(ast, ast_.Operators):
            logger.debug(f"Matching against operator: {against} with AST: {ast}")
        return against == ast

    @_match.register
    def _(self, against: bool, ast: ast_.ASTFieldChildren) -> bool:
        return against == ast
