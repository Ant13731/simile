from __future__ import annotations
from typing import Any, Callable, Sequence, ClassVar
from dataclasses import dataclass, field
from copy import deepcopy

from loguru import logger

from src.mod.data import ast_

from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer
from src.mod.pipeline.optimizer.v2.structure_matcher import StructureMatcher
from src.mod.data.simrw.guard_condition import PatternMatchVars, GuardCondition, GUARD_CONDITIONS
from src.mod.pipeline.printers.ast_ import ast_to_source


class RewriteRuleError(Exception):
    pass


@dataclass
class RewriteRule:
    class_name: ClassVar[str]
    rewrite_var_counter: ClassVar[int] = 0

    def apply(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode:
        logger.debug(f"Applying rewrite rule {self.name()} to AST: {ast_to_source(ast)}")
        result = ast.find_and_replace_with_func(lambda ast__: self._apply(ast__, type_synthesizer))
        logger.debug(f"Rewrite rule result: {ast_to_source(result)}")
        return result

    def _apply(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
        raise NotImplementedError

    def name(self) -> str:
        return self.class_name

    @classmethod
    def fresh_var(cls) -> str:
        RewriteRule.rewrite_var_counter += 1
        return f"simrw_var_{RewriteRule.rewrite_var_counter}"


@dataclass
class SimrwRewriteRule(RewriteRule):
    # Class name is for rewrite rules with overriding apply statements (basically hardcoded)
    # here we use normal name since rewrites will be instances of this class
    class_name: ClassVar[str] = "SimrwRewriteRule"

    _name: str
    vars_: PatternMatchVars
    rewrite_left: ast_.ASTNode
    rewrite_right: ast_.ASTNode
    # These should be guarding functions that accept vars_
    when: list[GuardCondition]

    def name(self) -> str:
        return self._name

    def _apply(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
        # Attempt to structurally pattern match with the LH side
        # Collect the substituted vars in a dict for reversal later - assign a str to part of the AST
        structure_matcher = StructureMatcher(set(self.vars_.keys()))
        substitutions = structure_matcher.match(ast, self.rewrite_left)
        if not substitutions:
            logger.debug("Failed to match: couldn't find substitutions")
            return None

        # Check against typed vars (ast types should be a subset of the rewrite types)
        for name, matched_ast in substitutions.items():
            matched_ast_type = type_synthesizer.synthesize_type(matched_ast)
            expected_var_type = self.vars_[name]
            if not matched_ast_type.is_subtype(expected_var_type):
                logger.debug("Failed to match: matched AST type is not a subtype of expected var type")
                return None

        # Check guard conditions
        for guard_condition in self.when:
            if not guard_condition.guard(ast, self.vars_):
                logger.debug(f"Failed to match: guard condition {guard_condition.name}")
                return None

        # Apply the right hand structural match
        # Substitute vars
        replacement_ast = deepcopy(self.rewrite_right)
        for name, matched_ast in substitutions.items():
            replacement_ast = replacement_ast.find_and_replace(ast_.Identifier(name), matched_ast)
        logger.debug(f"Rewrite rule {self.name()} applied successfully")
        return replacement_ast
