import pytest
import pathlib

from src.mod.data import ast_, types
from src.mod.data.simrw import SimrwRewriteRule, GENERIC_REWRITE_RULE_PATHS, RAW_PYTHON_REWRITE_RULE_PATHS, RAW_PYTHON_QUANTIFICATION_RULES
from src.mod.data.symbol_table.table import SymbolTable

from src.mod.pipeline.optimizer.v2 import convert_simrw_to_rewrite_rules
from src.mod.pipeline.parser import parse_simrw_file
from src.mod.pipeline.analysis.populate_symbol_table import PopulateSymbolTable
from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer


class TestOptimizerHappyPath:
    @pytest.mark.parametrize("rewrite_rule_path", GENERIC_REWRITE_RULE_PATHS)
    def test_generic_rewrite_rule_parses(self, rewrite_rule_path: pathlib.Path):
        parse_simrw_file(rewrite_rule_path)

    @pytest.mark.parametrize("rewrite_rule_path", GENERIC_REWRITE_RULE_PATHS)
    def test_generic_rewrite_rule_converts(self, rewrite_rule_path: pathlib.Path):
        rules = parse_simrw_file(rewrite_rule_path)
        convert_simrw_to_rewrite_rules(rules)

    @pytest.mark.parametrize("rewrite_rule_path", RAW_PYTHON_REWRITE_RULE_PATHS)
    def test_raw_python_rewrite_rule_parses(self, rewrite_rule_path: pathlib.Path):
        parse_simrw_file(rewrite_rule_path)

    @pytest.mark.parametrize("rewrite_rule_path", RAW_PYTHON_REWRITE_RULE_PATHS)
    def test_raw_python_rewrite_rule_converts(self, rewrite_rule_path: pathlib.Path):
        rules = parse_simrw_file(rewrite_rule_path)
        convert_simrw_to_rewrite_rules(rules)

    def test_rule_application(self):
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
        double_addition_rule = SimrwRewriteRule(
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
        expected_ast = ast_.Add(
            ast_.Multiply(
                ast_.Int("2"),
                ast_.Multiply(
                    ast_.Int("2"),
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
        symbol_table = SymbolTable()
        symbol_table_populator = PopulateSymbolTable(symbol_table)
        symbol_table_populator.populate_base()
        symbol_table_populator.populate(ast_to_match)
        type_synthesizer = TypeSynthesizer(symbol_table)

        ast_after_rewrite = double_addition_rule.apply(ast_to_match, type_synthesizer)
        assert ast_after_rewrite == expected_ast
