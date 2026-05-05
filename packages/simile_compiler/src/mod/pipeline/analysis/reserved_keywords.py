from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
import pathlib
from typing import TypeVar

from src.mod.pipeline.scanner import Location, KEYWORD_TABLE
from src.mod.pipeline.parser import parse, ParseError
from src.mod.data import ast_
from src.mod.data.ast_.symbol_table_types import (
    SimileType,
    ModuleImports,
    ProcedureTypeDef,
    StructTypeDef,
    EnumTypeDef,
    SimileTypeError,
    BaseSimileType,
)
from src.mod.data.ast_.symbol_table_env import (
    STARTING_ENVIRONMENT,
    PRIMITIVE_TYPES,
    BUILTIN_FUNCTIONS,
)

RESERVED_KEYWORDS = list(KEYWORD_TABLE.keys())


T = TypeVar("T", bound=ast_.ASTNode)


@dataclass
class ReservedKeywordErr:
    node: ast_.ASTNode
    clashing_keyword: str
    keyword_list_name: str

    def __str__(self) -> str:
        ret = ""
        ret += f"Error: Reserved keyword {self.clashing_keyword} (from keyword list {self.keyword_list_name}) used as identifier within program, "
        ret += f"{self.node.get_location()}\n"
        return ret


def check_clash(node: ast_.ASTNode, name: str) -> ReservedKeywordErr | None:
    if name in PRIMITIVE_TYPES:
        return ReservedKeywordErr(node, name, "PRIMITIVE_TYPES")
    if name in BUILTIN_FUNCTIONS:
        return ReservedKeywordErr(node, name, "BUILTIN_FUNCTIONS")
    if name in RESERVED_KEYWORDS:
        return ReservedKeywordErr(node, name, "RESERVED_KEYWORDS")
    return None


def reserved_keywords_check(ast: ast_.ASTNode) -> None:
    """Throws an error if reserved keywords are used as identifiers in the AST."""

    def traversal_function(node: ast_.ASTNode) -> ReservedKeywordErr | None:
        match node:
            case ast_.Assignment(ast_.Identifier(name), _) | ast_.Assignment(ast_.TypedName(ast_.Identifier(name), _), _):
                return check_clash(node, name)

            case ast_.For(iterable_names, _, _) | ast_.QualifiedQuantifier(iterable_names, _, _) | ast_.LambdaDef(iterable_names, _, _):
                for ident in iterable_names.flatten():
                    if not isinstance(ident, ast_.Identifier):
                        continue
                    if (ret := check_clash(node, ident.name)) is not None:
                        return ret

            case ast_.RecordDef(ast_.Identifier(name), _):
                return check_clash(node, name)
            case ast_.ProcedureDef(ast_.Identifier(name), args, _, _):
                if (ret := check_clash(node, name)) is not None:
                    return ret

                for arg in args:
                    assert isinstance(arg.name, ast_.Identifier)
                    if (ret := check_clash(node, arg.name.name)) is not None:
                        return ret
        return None

    errors = list(filter(None, ast_.dataclass_traverse(ast, traversal_function, True, True)))

    if errors:
        raise ValueError(f"Reserved keywords used as identifiers: {'\n'.join(map(str,errors))}")
