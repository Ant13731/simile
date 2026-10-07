from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar

from src.mod.pipeline.scanner import KEYWORD_TABLE
from src.mod.data import ast_
from src.mod.pipeline.analysis.type_annotation_resolver import TypeAnnotationResolver

T = TypeVar("T", bound=ast_.ASTNode)
RESERVED_KEYWORDS = list(KEYWORD_TABLE.keys())


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
    if name in TypeAnnotationResolver.BUILT_IN_TYPES:
        return ReservedKeywordErr(node, name, "RESERVED_KEYWORDS_FOR_TYPES")
    if name in RESERVED_KEYWORDS:
        return ReservedKeywordErr(node, name, "RESERVED_KEYWORDS")
    return None


def reserved_keywords_check(ast: ast_.ASTNode) -> None:
    """Throws an error if reserved keywords are used as identifiers in the AST."""

    errors = list(filter(None, ast_.dataclass_traverse(ast, _keyword_traversal_function, True, True)))

    if errors:
        raise ValueError(f"Reserved keywords used as identifiers: {'\n'.join(map(str,errors))}")


def _keyword_traversal_function(node: ast_.ASTNode) -> ReservedKeywordErr | None:
    match node:
        case ast_.Assignment(ast_.Identifier(name), _) | ast_.Assignment(ast_.TypedName(ast_.Identifier(name), _), _):
            return check_clash(node, name)

        case ast_.For(iterable_names, _, _) | ast_.Generator(iterable_names, _, _) | ast_.LambdaDef(iterable_names, _, _):
            for ident in iterable_names.flatten():
                if not isinstance(ident, ast_.Identifier):
                    continue
                if (ret := check_clash(node, ident.name)) is not None:
                    return ret

        case ast_.RecordDefIdentifier(ast_.Identifier(name), _):
            return check_clash(node, name)
        case ast_.ProcedureDefIdentifier(ast_.Identifier(name), args, _, _):
            if (ret := check_clash(node, name)) is not None:
                return ret

            for arg in args:
                assert isinstance(arg.name, ast_.Identifier)
                if (ret := check_clash(node, arg.name.name)) is not None:
                    return ret
    return None
