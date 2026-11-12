from __future__ import annotations

from pathlib import Path
from loguru import logger

import pytest

from src.mod.data.ast_ import ASTNode
from src.mod.data.rewrite_rules import SIMRW_FILES
from src.mod.data.helpers import flatten
from src.mod.pipeline.printers import simrw_ast_to_source, simrw_to_source
from src.mod.pipeline.optimizer.v2 import parse_simrw_file, convert_simrw_to_rewrite_rules, parse_simrw


def simrw_library_rules() -> list[str]:
    simrw_rules = []
    for simrw_file in SIMRW_FILES:
        with open(simrw_file, "r") as f:
            simrw_file_text = f.read()
        simrw_file_text = "\n".join(line for line in simrw_file_text.splitlines() if not line.strip().startswith("#"))
        for simrw_rule_text in simrw_file_text.split("rule"):
            if not simrw_rule_text.strip():
                continue
            simrw_rule_text = "rule" + simrw_rule_text
            simrw_rules.append(simrw_rule_text.strip())
    return simrw_rules


class TestSimRWLibrary:
    @pytest.mark.parametrize("source_path", SIMRW_FILES)
    def test_parse_from_file_without_exceptions(self, source_path: Path) -> None:
        simrw_asts = parse_simrw_file(source_path)
        assert len(simrw_asts) > 0, "Test not set up correctly (did not parse any rules)"

    @pytest.mark.parametrize("source", simrw_library_rules())
    def test_parse_without_exceptions(self, source: str) -> None:
        assert len(parse_simrw(source)) == 1, "Test not set up correctly (did not parse exactly one rule)"

    @pytest.mark.parametrize("source", simrw_library_rules())
    def test_parse_to_source_round_trip(self, source: str) -> None:
        simrw_asts = parse_simrw(source)
        assert len(simrw_asts) == 1
        simrw_ast = simrw_asts[0]

        source_from_ast = simrw_ast_to_source(simrw_ast)
        round_trip_asts = parse_simrw(source_from_ast)
        assert len(round_trip_asts) == 1
        round_trip_ast = round_trip_asts[0]

        assert simrw_ast == round_trip_ast

    @pytest.mark.parametrize("source", simrw_library_rules())
    def test_parse_and_convert_without_exceptions(self, source: str) -> None:
        simrw_asts = parse_simrw(source)
        assert len(convert_simrw_to_rewrite_rules(simrw_asts)) == len(simrw_asts)

    @pytest.mark.parametrize("source", simrw_library_rules())
    def test_parse_and_convert_to_source_round_trip(self, source: str) -> None:
        simrw_asts = parse_simrw(source)
        rewrite_rules = convert_simrw_to_rewrite_rules(simrw_asts)
        assert len(rewrite_rules) == 1
        rewrite_rule = rewrite_rules[0]

        source_from_ast = simrw_to_source(rewrite_rule)
        round_trip_asts = parse_simrw(source_from_ast)
        round_trip_rewrite_rules = convert_simrw_to_rewrite_rules(round_trip_asts)
        assert len(round_trip_rewrite_rules) == 1
        round_trip_rewrite_rule = round_trip_rewrite_rules[0]

        assert rewrite_rule == round_trip_rewrite_rule
