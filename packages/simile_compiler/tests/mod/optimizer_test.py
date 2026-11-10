# NOTE: Temporarily disabling optimizer tests while we roll out v2 of the optimizer with simrw rules
# import pytest
# import pathlib

# from src.mod.data import ast_
# from src.mod.data.rewrite_rules import SIMRW_FILES
# from src.mod.pipeline.analysis import SemanticAnalysis, semantic_analysis
# from src.mod.pipeline.optimizer.v2 import convert_simrw_to_rewrite_rules, parse_simrw_file


# class TestOptimizerHappyPath:
#     @pytest.mark.parametrize("rewrite_rule_path", SIMRW_FILES)
#     def test_rewrite_rule_parses(self, rewrite_rule_path: pathlib.Path):
#         parse_simrw_file(rewrite_rule_path)

#     @pytest.mark.parametrize("rewrite_rule_path", SIMRW_FILES)
#     def test_rewrite_rule_converts(self, rewrite_rule_path: pathlib.Path):
#         rules = parse_simrw_file(rewrite_rule_path)
#         convert_simrw_to_rewrite_rules(rules)
