from __future__ import annotations
from typing import Any, Callable, Sequence, ClassVar


from src.mod.data import ast_
from src.mod.data.simrw.rewrite_rule import RewriteRule, RewriteRuleError

from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer


class QuantifierLoweringRewriteRule(RewriteRule):
    class_name: ClassVar[str] = "quantifier_lowering"
    quantification_op_lookup: ClassVar[dict[ast_.QuantifierOperator, str]] = {
        ast_.QuantifierOperator.FORALL: "forall",
        ast_.QuantifierOperator.EXISTS: "exists",
        ast_.QuantifierOperator.UNION_ALL: "union",
        ast_.QuantifierOperator.INTERSECTION_ALL: "intersection",
        ast_.QuantifierOperator.SUM: "sum",
        ast_.QuantifierOperator.PRODUCT: "product",
        ast_.QuantifierOperator.MAX: "max",
        ast_.QuantifierOperator.MIN: "min",
    }

    def _apply(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
        if not isinstance(ast, ast_.Quantifier3):
            return None
        if not ast.op_type.is_collection_operator():
            return ast_.Call(
                ast_.Symbol(
                    type_synthesizer.symbol_table.lookup_identifier(self.quantification_op_lookup[ast.op_type]),
                ),
                [ast_.SetComprehension(ast.body)],
            )
        return None


RAW_PYTHON_QUANTIFICATION_RULES: list[RewriteRule] = [
    QuantifierLoweringRewriteRule(),
]
