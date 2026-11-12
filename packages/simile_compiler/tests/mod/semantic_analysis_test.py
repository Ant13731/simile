from __future__ import annotations

import pytest
import pathlib
from loguru import logger

from src.mod.data import ast_
from src.mod.pipeline.parser import parse
from src.mod.pipeline.analysis import SemanticAnalysis, semantic_analysis, make_symbol_table
from src.mod.data.standard_library import STANDARD_LIBRARY_FILES
from src.mod.pipeline.printers import ast_to_source

from tests.mod.ast_to_source_test import round_trip_parse
from tests.mod.examples import EXAMPLES_FILES


class TestBase:
    def test_empty_symbol_table(self):
        make_symbol_table(ast_.Start(ast_.Statements([]), ""), True)
        assert True

    def test_empty_symbol_table_with_standard_library(self):
        make_symbol_table(ast_.Start(ast_.Statements([]), ""), False)
        assert True


class TestStandardLibraryHappyPath:
    @pytest.mark.parametrize("standard_library_path", STANDARD_LIBRARY_FILES)
    def test_standard_library_parses(self, standard_library_path: pathlib.Path):
        with open(standard_library_path, "r", encoding="utf-8") as f:
            source = f.read()
        parse(source, standard_library_path)

    @pytest.mark.parametrize("standard_library_path", STANDARD_LIBRARY_FILES)
    def test_standard_library_parses_to_source(self, standard_library_path: pathlib.Path):
        with open(standard_library_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, standard_library_path)
        source_from_ast = ast_to_source(ast)
        round_trip_ast = parse(source_from_ast, standard_library_path)
        assert ast == round_trip_ast

    @pytest.mark.parametrize("standard_library_path", STANDARD_LIBRARY_FILES)
    def test_standard_library_passes_semantic_analysis(self, standard_library_path: pathlib.Path):
        with open(standard_library_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, standard_library_path)
        analysis = semantic_analysis(ast, True)
        assert analysis is not None


class TestExamplesHappyPath:
    @pytest.mark.parametrize("example_path", EXAMPLES_FILES)
    def test_example_parses(self, example_path: pathlib.Path):
        with open(example_path, "r", encoding="utf-8") as f:
            source = f.read()
        parse(source, example_path)

    @pytest.mark.parametrize("example_path", EXAMPLES_FILES)
    def test_example_parses_to_source(self, example_path: pathlib.Path):
        with open(example_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, example_path)
        source_from_ast = ast_to_source(ast)
        round_trip_ast = parse(source_from_ast, example_path)
        assert ast == round_trip_ast

    @pytest.mark.parametrize("example_path", EXAMPLES_FILES)
    def test_example_passes_semantic_analysis(self, example_path: pathlib.Path):
        with open(example_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, example_path)
        analysis = semantic_analysis(ast)
        assert analysis is not None
