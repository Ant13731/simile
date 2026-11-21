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
        end = ast.body.end_or_branch
        if isinstance(end, list):
            fold_op_type = ast_.CollectionOperator.from_quantifier_operator(ast.op_type)
            match fold_op_type:
                case ast_.CollectionOperator.SEQUENCE:
                    fold_operator: type[ast_.Concat | ast_.Add | ast_.Union] = ast_.Concat
                case ast_.CollectionOperator.BAG:
                    fold_operator = ast_.Add
                case ast_.CollectionOperator.SET | ast_.CollectionOperator.RELATION:
                    fold_operator = ast_.Union
                case _:
                    raise RewriteRuleError(f"Failed to convert {ast.op_type} to a collection operator")

            # Idea: use a fold with the "addition" operator for each type. this is what (x in S | E)`(x in T | F) really means
            # Problems: symbol table for these? fresh variables?
            accumulator_fresh = ast_.Identifier(RewriteRule.fresh_var())
            iterator_fresh = ast_.Identifier(RewriteRule.fresh_var())
            standalone_ends: list[ast_.ASTNode] = list(map(lambda e: ast_.Quantifier3(e, ast.op_type), end))
            end = ast_.Fold(
                ast_.Assignment(
                    accumulator_fresh,
                    ast_.Enumeration([], fold_op_type),
                    False,
                ),
                ast_.QuantifierBody(
                    [
                        ast_.Generator(iterator_fresh, ast_.Enumeration(standalone_ends, fold_op_type), ast_.True_()),
                    ],
                    fold_operator(iterator_fresh, accumulator_fresh),
                ),
            )

        assert isinstance(end, ast_.ASTNode)
        return ast_.Quantifier3(ast_.QuantifierBody(ast.body.generators, end), ast.op_type)


# TODO the below rewrites should aim at eliminating the (x in S | E)`(x in T | F) syntax.
# then the printers responsibility should be passing this to a library caller
# prob the simplest way forward

# class FoldLoweringRewriteRule(RewriteRule):
#     class_name: ClassVar[str] = "fold_lowering"

#     def _apply(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
#         if not isinstance(ast, ast_.Fold):
#             return None
#         target = ast.accumulator_init.target
#         if isinstance(ast.quantifier_body.end_or_branch, list):
#             statements = []
#             for iter_body in ast.quantifier_body.end_or_branch:
#                 statements.append(self.lower_ast(iter_body))
#             body: ast_.ASTNode = ast_.Statements(statements)
#         else:
#             body = ast_.Assignment(target, ast.quantifier_body.end_or_branch, False)

#         for generator in reversed(ast.quantifier_body.generators):
#             body = self.create_fold_loop(generator, body)
#         return ast_.Statements([ast.accumulator_init, body])

#     def create_fold_loop(self, generator: ast_.Generator, body: ast_.ASTNode) -> ast_.ASTNode:
#         return ast_.For(
#             generator.identifiers,
#             generator.set_,
#             ast_.If(generator.predicate, body),
#         )


# class IterLoweringRewriteRule(RewriteRule):
#     class_name: ClassVar[str] = "iter_lowering"

#     def _apply(self, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
#         if not isinstance(ast, ast_.IterBody):
#             return None
#         if isinstance(ast.end_or_branch, list):
#             statements = []
#             for iter_body in ast.end_or_branch:
#                 statements.append(self.lower_ast(iter_body))
#             body: ast_.ASTNode = ast_.Statements(statements)
#         else:
#             body = ast.end_or_branch.body

#         for generator in reversed(ast.generators):
#             body = self.create_iter_loop(generator, body)
#         return body

#     def create_iter_loop(self, generator: ast_.IterGenerator, body: ast_.ASTNode) -> ast_.ASTNode:
#         statements: list[ast_.ASTNode] = []
#         statements.append(
#             ast_.Assignment(
#                 generator.generator.identifiers,
#                 generator.generator.set_,
#                 choice_assignment=True,
#             )
#         )
#         for assignment in generator.assignments:
#             statements.append(assignment)
#         statements.append(
#             ast_.For(
#                 generator.generator.identifiers,
#                 ast_.Difference(generator.generator.set_, ast_.SetEnumeration([generator.generator.identifiers])),
#                 ast_.If(generator.generator.predicate, body),
#             )
#         )
#         return ast_.Statements(statements)


RAW_PYTHON_QUANTIFICATION_RULES: list[RewriteRule] = [
    QuantifierLoweringRewriteRule(),
    # FoldLoweringRewriteRule(),
    # IterLoweringRewriteRule(),
]
