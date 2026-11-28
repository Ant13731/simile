import pytest
from pathlib import Path
from loguru import logger

from src.mod.data import ast_, types
from src.mod.data.simrw import SimrwRule
from src.mod.data.symbol_table.table import SymbolTable
from src.mod.data.standard_library import STANDARD_LIBRARY_FILES

from src.mod.pipeline.optimizer.v2 import (
    RAW_PYTHON_LOWERING_PHASE,
    GENERIC_NUMERIC_PHASE,
    GENERIC_DESUGARING_PHASE,
    GENERIC_COMPREHENSION_CONSTRUCTION_PHASE,
    GENERIC_BOOL_NORMALIZATION_PHASE,
    RewritePhase,
)
from src.mod.pipeline.parser import parse
from src.mod.pipeline.analysis import PopulateSymbolTable, TypeSynthesizer, semantic_analysis
from src.mod.pipeline.printer import ast_to_source

from tests.mod.examples import EXAMPLES_FILES

TESTING_PHASES = [
    RAW_PYTHON_LOWERING_PHASE,
    # GENERIC_NUMERIC_PHASE,
    # GENERIC_DESUGARING_PHASE,
    # GENERIC_COMPREHENSION_CONSTRUCTION_PHASE,
    # GENERIC_BOOL_NORMALIZATION_PHASE,
]


test_ast_input = ast_.Add(
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
test_ast_expected = ast_.Add(
    ast_.Multiply(
        ast_.Int("2"),
        ast_.Multiply(
            ast_.Int("2"),
            ast_.Int("9"),
        ),
    ),
    ast_.Add(
        ast_.Multiply(
            ast_.Int("2"),
            ast_.Int("9"),
        ),
        ast_.Add(
            ast_.Float("9.1"),
            ast_.Float("9.1"),
        ),
    ),
)
test_ast_rewrite_rule = SimrwRule(
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
test_ast_rewrite_phase = RewritePhase("test_ast_phase", [test_ast_rewrite_rule])


class TestRewritePhase:
    @pytest.mark.parametrize("phase", TESTING_PHASES)
    def test_simile_file_passes_rewrite_phase_without_exceptions_standard_library(self, phase: RewritePhase):
        analysis = semantic_analysis(ast_.Start(ast_.Statements([]), ""))
        logger.debug(f"Rewriting file with phase {phase.name}")
        logger.debug(f"Before:\n{ast_to_source(analysis.ast)}")
        phase_applied_ast = phase.apply_phase(analysis.ast, analysis.type_synthesizer)
        logger.debug(f"After:\n{ast_to_source(phase_applied_ast)}")

    @pytest.mark.parametrize("input_file", EXAMPLES_FILES)
    @pytest.mark.parametrize("phase", TESTING_PHASES)
    def test_simile_file_passes_rewrite_phase_without_exceptions(self, input_file: Path, phase: RewritePhase):
        with open(input_file, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, input_file)
        logger.debug(f"Analyzing file {input_file}")
        analysis = semantic_analysis(ast)
        logger.debug(f"Rewriting file with phase {phase.name}")
        logger.debug(f"Before:\n{ast_to_source(analysis.ast)}")
        phase_applied_ast = phase.apply_phase(analysis.ast, analysis.type_synthesizer)
        logger.debug(f"After:\n{ast_to_source(phase_applied_ast)}")

    def test_phase_application(self):
        symbol_table = SymbolTable()
        symbol_table_populator = PopulateSymbolTable(symbol_table)
        symbol_table_populator.populate_base()
        symbol_table_populator.populate(test_ast_input)
        type_synthesizer = TypeSynthesizer(symbol_table)

        ast_after_rewrite = test_ast_rewrite_phase.apply_phase(test_ast_input, type_synthesizer)
        logger.debug(f"Before: {ast_to_source(test_ast_input)}")
        logger.debug(f"After: {ast_to_source(ast_after_rewrite)}")
        logger.debug(f"Expected: {ast_to_source(test_ast_expected)}")
        assert ast_after_rewrite == test_ast_expected
