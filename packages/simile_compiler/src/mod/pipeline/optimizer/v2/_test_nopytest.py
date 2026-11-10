from __future__ import annotations
from typing import Any, Callable, Sequence, ClassVar
from dataclasses import dataclass, field
from copy import deepcopy

from loguru import logger

from src.mod.data import ast_, traits, types
from src.mod.data.helpers.dataclass import dataclass_find_and_replace, dataclass_traverse
from src.mod.data.symbol_table.table import SymbolTable
from src.mod.pipeline.analysis.populate_symbol_table import PopulateSymbolTable
from src.mod.pipeline.printers import ast_to_source, simrw_to_source
from src.mod.pipeline.analysis import TypeAnnotationResolver, make_symbol_table
from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer
from src.mod.pipeline.parser import parse
from src.mod.pipeline.optimizer.v2.simrw_parser import SimrwAST
from src.mod.pipeline.optimizer.v2.structure_matcher import StructureMatcher
from src.mod.pipeline.optimizer.v2.guard_condition import PatternMatchVars, GuardCondition, GUARD_CONDITIONS
from src.mod.pipeline.optimizer.v2.simrw import RewriteRule, _apply_rewrite_rule, apply_rewrite_rule

ast_to_match = ast_.Add(
    ast_.Add(
        ast_.Add(
            ast_.Int("9"),
            ast_.Int("9"),
        ),
        ast_.Add(
            ast_.Int("9"),
            ast_.Int("9"),
        ),
    ),
    ast_.Add(
        ast_.Add(
            ast_.Int("9"),
            ast_.Int("9"),
        ),
        ast_.Add(
            ast_.Float("9.1"),
            ast_.Float("9.1"),
        ),
    ),
)
double_addition_rule = RewriteRule(
    "double_addition",
    {"x": types.IntType()},
    ast_.Add(
        ast_.Identifier("x"),
        ast_.Identifier("x"),
    ),
    ast_.Multiply(
        ast_.Int("2"),
        ast_.Identifier("x"),
    ),
    [],
)
symbol_table = SymbolTable()
symbol_table_populator = PopulateSymbolTable(symbol_table)
symbol_table_populator.populate_base()
symbol_table_populator.populate(ast_to_match)
type_synthesizer = TypeSynthesizer(symbol_table)

ast_after_rewrite = apply_rewrite_rule(double_addition_rule, ast_to_match, type_synthesizer)

print("AST to match:", ast_to_source(ast_to_match))
print("Double addition rule:", simrw_to_source(double_addition_rule))
print("AST after match:", ast_to_source(ast_after_rewrite or ast_.Statements([])))
