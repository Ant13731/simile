from __future__ import annotations

import pytest
import pathlib
from loguru import logger

from src.mod.data import ast_
from src.mod.pipeline.parser import parse
from src.mod.pipeline.analysis import SemanticAnalysis, semantic_analysis, make_symbol_table
from src.mod.data.standard_library import STANDARD_LIBRARY_FILES
from src.mod.pipeline.printer import ast_to_source

from tests.mod.ast_to_source_test import round_trip_parse
from tests.mod.examples import EXAMPLES_FILES


class TestBase:
    def test_empty_symbol_table(self):
        make_symbol_table(ast_.Start(ast_.Statements([]), ""), True)
        assert True

    def test_empty_symbol_table_with_standard_library(self):
        make_symbol_table(ast_.Start(ast_.Statements([]), ""), False)
        assert True


class TestSimileFiles:
    @pytest.mark.parametrize("source_path", STANDARD_LIBRARY_FILES)
    def test_semantic_analysis_without_exceptions_no_standard_library(self, source_path: pathlib.Path):
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, source_path)
        logger.debug(f"Analyzing file {source_path}")
        analysis = semantic_analysis(ast, True)
        assert analysis is not None

    @pytest.mark.parametrize("source_path", EXAMPLES_FILES)
    def test_semantic_analysis_without_exceptions(self, source_path: pathlib.Path):
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, source_path)
        logger.debug(f"Analyzing file {source_path}")
        analysis = semantic_analysis(ast)
        assert analysis is not None

    @pytest.mark.parametrize("source_path", STANDARD_LIBRARY_FILES)
    def test_semantic_analysis_to_source_without_exceptions_no_standard_library(self, source_path: pathlib.Path):
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, source_path)
        logger.debug(f"Analyzing file {source_path}")
        analysis = semantic_analysis(ast, True)
        source_from_ast = ast_to_source(analysis.ast)
        assert source_from_ast is not None

    @pytest.mark.parametrize("source_path", EXAMPLES_FILES)
    def test_semantic_analysis_to_source_without_exceptions(self, source_path: pathlib.Path):
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, source_path)
        logger.debug(f"Analyzing file {source_path}")
        analysis = semantic_analysis(ast)
        source_from_ast = ast_to_source(analysis.ast)
        assert source_from_ast is not None
