from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
import pathlib
from typing import TypeVar

from src.mod.pipeline.scanner import Location
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


T = TypeVar("T", bound=ast_.ASTNode)


def type_check(ast: ast_.ASTNode) -> None:
    """Calls `ast.get_type` throughout the entire AST.

    The `get_type` property performs hidden checks before returning a result."""

    # Getting the type of an ast node performs some type checks under the hood, so we just "call" the property and discard its result
    ast.get_type

    for child in ast.children(True):
        type_check(child)
