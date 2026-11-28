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
from src.mod.pipeline.analysis import semantic_analysis
from src.mod.pipeline.printer import ast_to_source
from src.mod.pipeline.codegen import lower_to_raw_python

from tests.mod.examples import EXAMPLES_FILES

TESTING_PHASES = [
    RAW_PYTHON_LOWERING_PHASE,
    # GENERIC_NUMERIC_PHASE,
    # GENERIC_DESUGARING_PHASE,
    # GENERIC_COMPREHENSION_CONSTRUCTION_PHASE,
    # GENERIC_BOOL_NORMALIZATION_PHASE,
]


class TestRewritePhase:

    @pytest.mark.parametrize("input_file", STANDARD_LIBRARY_FILES + EXAMPLES_FILES)
    @pytest.mark.parametrize("phase", TESTING_PHASES)
    def test_simile_file_compiles_to_raw_python(self, input_file: Path, phase: RewritePhase):
        with open(input_file, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, input_file)
        logger.debug(f"Analyzing file {input_file}")
        analysis = semantic_analysis(ast)
        logger.debug(f"Rewriting file with phase {phase.name}")
        logger.debug(f"Before:\n{ast_to_source(analysis.ast)}")
        phase_applied_ast = phase.apply_phase(analysis.ast, analysis.type_synthesizer)
        logger.debug(f"After:\n{ast_to_source(phase_applied_ast)}")
        analysis.ast = phase_applied_ast
        raw_python_output = lower_to_raw_python(analysis)
        logger.debug(f"Raw python output:\n{raw_python_output}")
