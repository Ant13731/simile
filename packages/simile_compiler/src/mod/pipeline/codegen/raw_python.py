from dataclasses import dataclass
from functools import singledispatchmethod

from src.mod.data import ast_, types, traits
from src.mod.data.symbol_table import SymbolTable
from src.mod.pipeline.analysis import SemanticAnalysis


@dataclass
class RawSimileToPythonCodeGenerator:
    symbol_table: SymbolTable
    lib_lookup: dict = {
        ast_.RelationOperator.RELATION: "relation_generator",
        ast_.RelationOperator.TOTAL_RELATION: "total_relation_generator",
        ast_.RelationOperator.SURJECTIVE_RELATION: "surjective_relation_generator",
        ast_.RelationOperator.TOTAL_SURJECTIVE_RELATION: "total_surjective_relation_generator",
        ast_.RelationOperator.PARTIAL_FUNCTION: "partial_function_generator",
        ast_.RelationOperator.TOTAL_FUNCTION: "total_function_generator",
        ast_.RelationOperator.PARTIAL_INJECTION: "partial_injection_generator",
        ast_.RelationOperator.TOTAL_INJECTION: "total_injection_generator",
        ast_.RelationOperator.PARTIAL_SURJECTION: "partial_surjection_generator",
        ast_.RelationOperator.TOTAL_SURJECTION: "total_surjection_generator",
        ast_.RelationOperator.BIJECTION: "bijection_generator",
        #
        ast_.ListOperator.AND: "and",
        ast_.ListOperator.OR: "or",
        #
        ast_.UnaryOperator.NOT: "not",
        ast_.UnaryOperator.NEGATIVE: "negative",
        ast_.UnaryOperator.INVERSE: "inverse",
        #
        ast_.BinaryOperator.IMPLIES: "implies",
        ast_.BinaryOperator.EQUIVALENT: "equivalent",
        ast_.BinaryOperator.NOT_EQUIVALENT: "not_equivalent",
        #
        ast_.BinaryOperator.ADD: "add",
        ast_.BinaryOperator.SUBTRACT: "subtract",
        ast_.BinaryOperator.MULTIPLY: "multiply",
        ast_.BinaryOperator.DIVIDE: "divide",
        ast_.BinaryOperator.INT_DIVIDE: "int_divide",
        ast_.BinaryOperator.MODULO: "modulo",
        ast_.BinaryOperator.EXPONENT: "exponent",
        #
        ast_.BinaryOperator.LESS_THAN: "less_than",
        ast_.BinaryOperator.LESS_THAN_OR_EQUAL: "less_than_or_equal",
        ast_.BinaryOperator.GREATER_THAN: "greater_than",
        ast_.BinaryOperator.GREATER_THAN_OR_EQUAL: "greater_than_or_equal",
        #
        ast_.BinaryOperator.EQUAL: "equal",
        ast_.BinaryOperator.NOT_EQUAL: "not_equal",
        ast_.BinaryOperator.IS: "is",
        ast_.BinaryOperator.IS_NOT: "is_not",
        #
        ast_.BinaryOperator.IN: "in",
        ast_.BinaryOperator.NOT_IN: "not_in",
        ast_.BinaryOperator.UNION: "union",
        ast_.BinaryOperator.INTERSECTION: "intersection",
        ast_.BinaryOperator.DIFFERENCE: "difference",
        #
        ast_.BinaryOperator.SUBSET: "subset",
        ast_.BinaryOperator.SUBSET_EQ: "subset_eq",
        ast_.BinaryOperator.SUPERSET: "superset",
        ast_.BinaryOperator.SUPERSET_EQ: "superset_eq",
        ast_.BinaryOperator.NOT_SUBSET: "not_subset",
        ast_.BinaryOperator.NOT_SUBSET_EQ: "not_subset_eq",
        ast_.BinaryOperator.NOT_SUPERSET: "not_superset",
        ast_.BinaryOperator.NOT_SUPERSET_EQ: "not_superset_eq",
        #
        ast_.BinaryOperator.MAPLET: "maplet",
        ast_.BinaryOperator.RELATION_OVERRIDING: "relation_overriding",
        ast_.BinaryOperator.COMPOSITION: "composition",
        ast_.BinaryOperator.CARTESIAN_PRODUCT: "cartesian_product",
        ast_.BinaryOperator.UPTO: "..",
        #
        ast_.BinaryOperator.DOMAIN_SUBTRACTION: "domain_subtraction",
        ast_.BinaryOperator.DOMAIN_RESTRICTION: "domain_restriction",
        ast_.BinaryOperator.RANGE_SUBTRACTION: "range_subtraction",
        ast_.BinaryOperator.RANGE_RESTRICTION: "range_restriction",
        #
        ast_.BinaryOperator.CONCAT: "concat",
    }
    custom_counter = 0

    def lower_type(self, typ: types.BaseType) -> str:
        raise NotImplementedError

    def lower_op(self, typ: types.BaseType) -> str:
        raise NotImplementedError

    @singledispatchmethod
    def lower_ast(self, ast: ast_.ASTNode) -> ast_.ASTNode:
        # For lowering simile-only concepts into python-like concepts,
        # simile types into python types, simile operators into python operators, etc.
        #
        # Concepts that dont translate directly will be simplified here, matching semantics as close as possible to simile
        return ast

    @lower_ast.register
    def _(self, ast: ast_.Quantifier3) -> ast_.ASTNode: ...

    @lower_ast.register
    def _(self, ast: ast_.Fold) -> ast_.ASTNode:
        target = ast.accumulator_init.target
        if isinstance(ast.quantifier_body.end_or_branch, list):
            statements = []
            for iter_body in ast.quantifier_body.end_or_branch:
                statements.append(self.lower_ast(iter_body))
            body: ast_.ASTNode = ast_.Statements(statements)
        else:
            body = ast_.Assignment(target, ast.quantifier_body.end_or_branch, False)

        for generator in reversed(ast.quantifier_body.generators):
            body = self.create_fold_loop(generator, body)
        return ast_.Statements([ast.accumulator_init, body])

    def create_fold_loop(self, generator: ast_.Generator, body: ast_.ASTNode) -> ast_.ASTNode:
        return ast_.For(
            generator.identifiers,
            generator.set_,
            ast_.If(generator.predicate, body),
        )

    @lower_ast.register
    def _(self, ast: ast_.Iter) -> ast_.ASTNode:
        return self.lower_ast(ast.body)

    @lower_ast.register
    def _(self, ast: ast_.IterBody) -> ast_.ASTNode:
        if isinstance(ast.end_or_branch, list):
            statements = []
            for iter_body in ast.end_or_branch:
                statements.append(self.lower_ast(iter_body))
            body: ast_.ASTNode = ast_.Statements(statements)
        else:
            body = ast.end_or_branch.body

        for generator in reversed(ast.generators):
            body = self.create_iter_loop(generator, body)
        return body

    def create_iter_loop(self, generator: ast_.IterGenerator, body: ast_.ASTNode) -> ast_.ASTNode:
        statements: list[ast_.ASTNode] = []
        statements.append(
            ast_.Assignment(
                generator.generator.identifiers,
                generator.generator.set_,
                choice_assignment=True,
            )
        )
        for assignment in generator.assignments:
            statements.append(assignment)
        statements.append(
            ast_.For(
                generator.generator.identifiers,
                ast_.Difference(generator.generator.set_, ast_.SetEnumeration([generator.generator.identifiers])),
                ast_.If(generator.generator.predicate, body),
            )
        )
        return ast_.Statements(statements)

    @lower_ast.register
    def _(self, ast: ast_.Assignment) -> ast_.ASTNode:
        if ast.choice_assignment:
            return ast_.Assignment(
                ast.target,
                ast_.Call(
                    ast_.Symbol(self.symbol_table.lookup_identifier("choice")),
                    [ast.value],
                ),
                choice_assignment=False,
            )
        return ast

    #### PRINTING ####
    def i(self, indent: int) -> str:
        # indentation
        return "    " * indent

    def print(self, ast: ast_.ASTNode) -> str:
        # Assume the ast has already been lowered into python-like attrs
        return self._print(ast, 0)

    @singledispatchmethod
    def _print(self, ast: ast_.ASTNode, i: int) -> str:
        raise NotImplementedError(f"Lowering not implemented for {type(ast)}")

    @_print.register
    def _(self, ast: ast_.Symbol, i: int) -> str:
        return f"{ast.symbol_table_entry.name}_{ast.symbol_table_entry.scope}_{ast.symbol_table_entry.id_}"

    @_print.register
    def _(self, ast: ast_.TupleSymbol, i: int) -> str:
        symbols = [self._print(item, i) for item in ast.items]
        return f"({', '.join(symbols)})"

    @_print.register
    def _(self, ast: ast_.RecordDefSymbol, i: int) -> str:
        record_name = self._print(ast.name, i)
        record_def_lines = [
            "@dataclass",
            f"class {record_name}:",
        ]

        for field, typ in ast.fields.items():
            type_str = self.lower_type(typ)
            record_def_lines.append(f"{self.i(1)}{field}: {type_str}")
        return f"{self.i(i)}\n".join(record_def_lines)

    @_print.register
    def _(self, ast: ast_.ProcedureDefSymbol, i: int) -> str:
        args = []
        for arg in ast.args:
            arg_name = self._print(arg, i)
            arg_type = self.lower_type(arg.symbol_table_entry.declared_type)
            args.append(f"{arg_name}: {arg_type}")
        return f"{self.i(i)}def {ast.name}({', '.join(args)}):\n{self._print(ast.body, i + 1)}"

    @_print.register
    def _(self, ast: ast_.Int | ast_.Float | ast_.String, i: int) -> str:
        return ast.value

    @_print.register
    def _(self, ast: ast_.True_, i: int) -> str:
        return "True"

    @_print.register
    def _(self, ast: ast_.False_, i: int) -> str:
        return "False"

    @_print.register
    def _(self, ast: ast_.None_, i: int) -> str:
        return "None"

    @_print.register
    def _(self, ast: ast_.BinaryOp | ast_.RelationOp, i: int) -> str:
        left = self._print(ast.left, i)
        right = self._print(ast.right, i)
        return f"simile.{self.lib_lookup[ast.op_type]}({left}, {right})"

    @_print.register
    def _(self, ast: ast_.UnaryOp, i: int) -> str:
        return f"simile.{self.lib_lookup[ast.op_type]}({ast.value})"

    @_print.register
    def _(self, ast: ast_.ListOp, i: int) -> str:
        ast_items = [self._print(item, i) for item in ast.items]
        return f"simile.{self.lib_lookup[ast.op_type]}([{', '.join(ast_items)}])"

    @_print.register
    def _(self, ast: ast_.ControlFlowStmt, i: int) -> str:
        match ast.op_type:
            case ast_.ControlFlowOperator.BREAK:
                return f"{self.i(i)}break"
            case ast_.ControlFlowOperator.CONTINUE:
                return f"{self.i(i)}continue"
            case ast_.ControlFlowOperator.SKIP:
                return f"{self.i(i)}pass"

    @_print.register
    def _(self, ast: ast_.Enumeration, i: int) -> str:
        match ast.op_type:
            case ast_.CollectionOperator.SET | ast_.CollectionOperator.RELATION:
                items = [self._print(item, i) for item in ast.items]
                return f"{{{', '.join(items)}}}"
            case ast_.CollectionOperator.SEQUENCE:
                items = [self._print(item, i) for item in ast.items]
                return f"[{', '.join(items)}]"
            case ast_.CollectionOperator.TUPLE:
                items = [self._print(item, i) for item in ast.items]
                return f"({', '.join(items)})"
            case ast_.CollectionOperator.BAG:
                items = [self._print(item, i) for item in ast.items]
                return f"Counter([{', '.join(items)}])"

    @_print.register
    def _(self, ast: ast_.Type_, i: int) -> str:
        type_name = self._print(ast.type_, i)
        if type_name.startswith("(") and type_name.endswith(")"):
            type_name = f"tuple[{type_name[1:-1]}]"
        if not ast.generics:
            return type_name
        return f"{type_name}[{', '.join([self._print(generic, i) for generic in ast.generics])}]"

    # @_lower.register
    # def _(self, ast: ast_.LambdaDef, i: int) -> str: ...
    @_print.register
    def _(self, ast: ast_.RecordAccess, i: int) -> str:
        return f"{self._print(ast.record, i)}.{ast.field_name}"

    @_print.register
    def _(self, ast: ast_.Call, i: int) -> str:
        args = [self._print(arg, i) for arg in ast.args]
        return f"{self._print(ast.target, i)}({', '.join(args)})"

    @_print.register
    def _(self, ast: ast_.TypedName, i: int) -> str:
        name = self._print(ast.name, i)
        typ = self._print(ast.type_, i)
        return f"{name}: {typ}"

    @_print.register
    def _(self, ast: ast_.Image, i: int) -> str:
        indices = self._print(ast.indices, i)
        target = self._print(ast.target, i)
        return f"simile.image({target}, {indices})"

    @_print.register
    def _(self, ast: ast_.Assignment, i: int) -> str:
        target = self._print(ast.target, i)
        value = self._print(ast.value, i)
        return f"{self.i(i)}{target} = {value}"

    @_print.register
    def _(self, ast: ast_.TraitApplication, i: int) -> str:
        return self._print(ast.target, i)

    @_print.register
    def _(self, ast: ast_.Return, i: int) -> str:
        return f"{self.i(i)}return {self._print(ast.value, i)}"

    @_print.register
    def _(self, ast: ast_.Statements, i: int) -> str:
        if not ast.items:
            return ""
        return f"\n".join([self._print(stmt, i) for stmt in ast.items])

    @_print.register
    def _(self, ast: ast_.Else, i: int) -> str:
        return f"{self.i(i)}else:\n{self._print(ast.body, i + 1)}"

    @_print.register
    def _(self, ast: ast_.If, i: int) -> str:
        return f"{self.i(i)}if {self._print(ast.condition, i)}:\n{self._print(ast.body, i + 1)}"

    @_print.register
    def _(self, ast: ast_.ElseIf, i: int) -> str:
        return f"{self.i(i)}elif {self._print(ast.condition, i)}:\n{self._print(ast.body, i + 1)}"

    @_print.register
    def _(self, ast: ast_.For, i: int) -> str:
        iterable = self._print(ast.iterable, i)
        return f"{self.i(i)}for {self._print(ast.iterable_names, i)} in simile.iter({iterable}):\n{self._print(ast.body, i + 1)}"

    @_print.register
    def _(self, ast: ast_.While, i: int) -> str:
        return f"{self.i(i)}while {self._print(ast.condition, i)}:\n{self._print(ast.body, i + 1)}"

    @_print.register
    def _(self, ast: ast_.TupleLiteral, i: int) -> str:
        items = [self._print(item, i) for item in ast.items]
        return f"({', '.join(items)})"

    @_print.register
    def _(self, ast: ast_.Start, i: int) -> str:
        main_body = self._print(ast.body, i + 1)
        return f"""
from dataclasses import dataclass
from collections import Counter
import simile

def main():
{main_body}

if __name__ == "__main__":
    main()
"""
