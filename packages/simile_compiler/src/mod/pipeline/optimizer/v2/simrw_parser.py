from __future__ import annotations
from typing import Any, Callable, Sequence
from dataclasses import dataclass, field
from copy import deepcopy
import pathlib

from loguru import logger
from lark import Lark, Transformer, Token
from lark.indenter import PythonIndenter

from src.mod.data import ast_
from src.mod.pipeline.parser import parse


@dataclass
class SimrwAST:
    name: str
    vars_: str
    rewrite_left: str
    rewrite_right: str
    when: list[str]


class RewriteTransformer(Transformer):
    def start(self, items) -> list[SimrwAST]:
        return items

    def rule(self, items: tuple[Token, tuple[str, str, str, list[str]]]) -> SimrwAST:
        return SimrwAST(
            items[0].value,
            items[1][0],
            items[1][1],
            items[1][2],
            items[1][3],
        )

    def vars_and_rest(self, items) -> tuple[str, str, str, list[str]]:
        return items[0], *items[1]

    def rewrite_and_rest(self, items) -> tuple[str, str, list[str]]:
        if items[2] is None:
            return items[0], items[1], []
        return items[0], items[1], items[2]

    def when_and_rest(self, items: list[list[str]]) -> list[str]:
        return items[0]

    def vars(self, items) -> str:
        return "\n".join([_strip_expected_prefix_whitespace(i) for i in items]).strip()

    def rewrite_left(self, items) -> str:
        return "\n".join([_strip_expected_prefix_whitespace(i) for i in items]).strip()

    def rewrite_right(self, items: list[Token]) -> str:
        return "\n".join([_strip_expected_prefix_whitespace(i) for i in items]).strip()

    def when(self, items: list[Token]) -> list[str]:
        return [_strip_expected_prefix_whitespace(i) for i in items]


def _strip_expected_prefix_whitespace(s_any: Any) -> str:
    s = str(s_any)
    if s.startswith(" " * 8):
        return s[8:]
    logger.warning(f"Expected rewrite rule line to start with 8 spaces, but got: {s}")
    return s


def parse_simrw(source: str) -> list[SimrwAST]:
    parser = Lark.open(
        "simrw.lark",
        rel_to=__file__,
        parser="lalr",
        transformer=RewriteTransformer(),
        postlex=PythonIndenter(),
    )
    simrw_asts: list[SimrwAST] = parser.parse(source)  # type: ignore
    return simrw_asts


def parse_simrw_file(file_path: str | pathlib.Path) -> list[SimrwAST]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        return parse_simrw(content)
