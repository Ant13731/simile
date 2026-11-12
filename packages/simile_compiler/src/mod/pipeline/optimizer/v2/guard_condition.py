from __future__ import annotations
from typing import ClassVar
from dataclasses import dataclass

from src.mod.data import ast_, types

type PatternMatchVars = dict[str, types.BaseType]


# TODO move to data section
@dataclass
class GuardCondition:
    name: ClassVar[str]
    # Subclasses should add information (as passed through caller notation in the when clause of simrw)

    def guard(self, ast: ast_.ASTNode, typed_vars: PatternMatchVars) -> bool:
        raise NotImplementedError("This must be subclassed with a defined guard condition")


# Maps function names in if-statements to guard functions that can block a rewrite rule from being applied
# The key only contains the name of the function - the exact arguments should be parsed from the when_condition string
# and applied to the right typed_vars
GUARD_CONDITIONS: dict[str, type[GuardCondition]] = {}
