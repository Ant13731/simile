from __future__ import annotations

from pathlib import Path

import pytest

from src.mod.data.ast_ import ASTNode
from src.mod.pipeline.parser import parse
from src.mod.pipeline.printers import ast_to_source

from tests.mod.parser_test import (
    BASIC_EXPRESSION_CASES,
    TYPE_EXPRESSION_CASES,
    SIMPLE_STATEMENT_CASES,
    MULTI_SIMPLE_STATEMENT_CASES,
    COMPOUND_STATEMENT_CASES,
    STRUCTURED_PROGRAM_CASES,
    COMPREHENSION_CASES,
    RELATION_SUBTYPE_CASES,
    SET_RELATION_OPERATION_CASES,
    COLLECTION_NEWLINE_CASES,
    ADVANCED_EXPRESSION_CASES,
    ADVANCED_STATEMENT_CASES,
    QUANTIFICATION_AND_TYPING_CASES,
    start_with_body,
    start_with_statements,
    normalize_source,
)


def round_trip_parse(source: str) -> ASTNode:
    """Parse the source code, convert the AST back to source code, and parse it again."""
    ast = parse(source, Path("test_source_file_path"))
    source_from_ast = ast_to_source(ast)
    return parse(source_from_ast, Path("test_source_file_path"))


class TestASTToSourceHappyPath:
    @pytest.mark.parametrize(
        "source, expected_body",
        BASIC_EXPRESSION_CASES,
    )
    def test_parse_basic_expressions(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        TYPE_EXPRESSION_CASES,
    )
    def test_parse_type_expressions(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        SIMPLE_STATEMENT_CASES,
    )
    def test_parse_simple_statements(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        MULTI_SIMPLE_STATEMENT_CASES,
    )
    def test_parse_multiple_simple_statements(self, source: str, expected_body: list[ASTNode]):
        assert round_trip_parse(source) == start_with_statements(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        COMPOUND_STATEMENT_CASES,
    )
    def test_parse_compound_statements(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        STRUCTURED_PROGRAM_CASES,
    )
    def test_parse_structured_programs(self, source: str, expected_body: ASTNode):
        source = normalize_source(source)
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        COMPREHENSION_CASES,
    )
    def test_parse_comprehensions(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        RELATION_SUBTYPE_CASES,
    )
    def test_parse_relation_subtypes(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        SET_RELATION_OPERATION_CASES,
    )
    def test_parse_set_and_relation_operations(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        COLLECTION_NEWLINE_CASES,
    )
    def test_parse_collections_with_newlines(self, source: str, expected_body: ASTNode):
        source = normalize_source(source)
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        ADVANCED_EXPRESSION_CASES,
    )
    def test_parse_advanced_expressions(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        ADVANCED_STATEMENT_CASES,
    )
    def test_parse_advanced_statements(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        QUANTIFICATION_AND_TYPING_CASES,
    )
    def test_parse_quantification_and_typing_forms(self, source: str, expected_body: ASTNode):
        assert round_trip_parse(source) == start_with_body(source, expected_body)
