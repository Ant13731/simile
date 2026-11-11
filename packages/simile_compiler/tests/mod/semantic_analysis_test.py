from __future__ import annotations

import pytest
import pathlib
from loguru import logger

from src.mod.data import ast_
from src.mod.pipeline.parser import parse
from src.mod.pipeline.analysis import SemanticAnalysis, semantic_analysis
from src.mod.data.standard_library import STANDARD_LIBRARY_FILES
from src.mod.pipeline.printers import ast_to_source

from tests.mod.ast_to_source_test import round_trip_parse


class TestAnalysisHappyPath:
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
        print("Source:")
        print(source)
        print("Source from AST:")
        print(source_from_ast)
        assert ast == round_trip_ast

    @pytest.mark.parametrize("standard_library_path", STANDARD_LIBRARY_FILES)
    def test_standard_library_passes_semantic_analysis(self, standard_library_path: pathlib.Path):
        with open(standard_library_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast = parse(source, standard_library_path)
        analysis = semantic_analysis(ast)
        assert analysis is not None
