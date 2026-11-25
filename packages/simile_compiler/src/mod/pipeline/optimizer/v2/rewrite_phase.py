from typing import TYPE_CHECKING, Sequence
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from src.mod.data import ast_
from src.mod.data.simrw import RewriteRule

from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer
from src.mod.pipeline.parser.simrw import parse_simrw_file
from src.mod.pipeline.optimizer.v2.simrw_to_rewrite_rule import convert_simrw_to_rewrite_rules


@dataclass
class RewritePhase:
    name: str
    rules_or_simrw_paths: Sequence[RewriteRule | Path]

    num_rule_list_attempted: int = 0
    num_rule_list_applied: int = 0
    num_traversals_attempted: int = 0

    _any_rule_matched_this_turn: bool = False

    def rules(self) -> list[RewriteRule]:
        rules = []
        for rule_or_path in self.rules_or_simrw_paths:
            if isinstance(rule_or_path, RewriteRule):
                rules.append(rule_or_path)
                continue

            logger.debug(f"Parsing simrw rules from path {rule_or_path} for phase {self.name}")
            simrw_asts = parse_simrw_file(rule_or_path)
            rewrite_rules = convert_simrw_to_rewrite_rules(simrw_asts)
            rules.extend(rewrite_rules)

        return rules

    def apply_phase(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode:
        # TODO should this func take in SemanticAnalysis?
        # TODO should SemanticAnalysis even carry the symbol table since its stored in the TypeSynthesizer?
        logger.debug(f"Applying phase {self.name}")
        self._any_rule_matched_this_turn = True
        while self._any_rule_matched_this_turn:
            logger.debug(f"Starting traversal {self.num_traversals_attempted}")
            self._any_rule_matched_this_turn = False
            self.num_traversals_attempted += 1
            self.num_rule_list_attempted = 0
            self.num_rule_list_applied = 0

            # This is a full traversal of all rules on all ast nodes once
            ast = ast.find_and_replace_with_func(
                lambda ast__: self._apply_rule_list_once(ast__, type_synthesizer),
            )
            logger.debug(f"Traversal {self.num_traversals_attempted}: Rule list applied {self.num_rule_list_applied}/{self.num_rule_list_attempted}")
        logger.debug(f"Completed phase {self.name} after {self.num_traversals_attempted} traversals")
        return ast

    def _apply_rule_list_once(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
        self.num_rule_list_attempted += 1
        num_all_applied_prev = self.num_rule_list_applied
        for rule in self.rules():
            rule_applied_ast = rule.apply(ast, type_synthesizer)
            if rule_applied_ast:
                self.num_rule_list_applied += 1
                self._any_rule_matched_this_turn = True
                ast = rule_applied_ast

        if num_all_applied_prev == self.num_rule_list_applied:
            return None  # To show that we didnt match anything this round
        return ast
