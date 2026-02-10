import pytest
from dataclasses import dataclass
from copy import deepcopy

from src import ast_
from src import analysis


def mk_starting_env(new_env: dict) -> ast_.SymbolTableEnvironment:
    return ast_.SymbolTableEnvironment(
        previous=ast_.STARTING_ENVIRONMENT,
        table=new_env,
    )


TEST_ASTS = [
    ast_.Statements(
        [
            ast_.Assignment(
                ast_.Identifier("x"),
                ast_.Int("5"),
            )
        ],
    ),
    ast_.Statements(
        [
            ast_.Assignment(
                ast_.Identifier("test_enum"),
                ast_.Enumeration(
                    [ast_.Identifier("a"), ast_.Identifier("b"), ast_.Identifier("c")],
                    op_type=ast_.CollectionOperator.SET,
                ),
            )
        ],
    ),
    ast_.Statements(
        [
            ast_.RecordDef(
                ast_.Identifier("TestStruct"),
                [
                    ast_.TypedName(ast_.Identifier("a"), ast_.Type_(ast_.Identifier("int"))),
                    ast_.TypedName(ast_.Identifier("b"), ast_.Type_(ast_.Identifier("str"))),
                ],
            ),
            ast_.Assignment(
                ast_.Identifier("test_struct"),
                ast_.Call(
                    ast_.Identifier("TestStruct"),
                    [
                        ast_.Int("42"),
                        ast_.String("hello"),
                    ],
                ),
            ),
        ],
    ),
    ast_.Statements(
        [
            ast_.RecordDef(
                ast_.Identifier("TestStruct"),
                [
                    ast_.TypedName(ast_.Identifier("a"), ast_.Type_(ast_.Identifier("int"))),
                    ast_.TypedName(ast_.Identifier("b"), ast_.Type_(ast_.Identifier("str"))),
                ],
            ),
            ast_.RecordDef(
                ast_.Identifier("TestStructTwo"),
                [
                    ast_.TypedName(ast_.Identifier("c"), ast_.Type_(ast_.Identifier("TestStruct"))),
                    ast_.TypedName(ast_.Identifier("d"), ast_.Type_(ast_.Identifier("str"))),
                ],
            ),
            ast_.Assignment(
                ast_.Identifier("test_struct"),
                ast_.Call(
                    ast_.Identifier("TestStructTwo"),
                    [
                        ast_.Call(
                            ast_.Identifier("TestStruct"),
                            [
                                ast_.Int("42"),
                                ast_.String("hello"),
                            ],
                        ),
                        ast_.String("hello"),
                    ],
                ),
            ),
        ],
    ),
    ast_.Statements(
        [
            ast_.Assignment(
                ast_.Identifier("x"),
                ast_.Int("5"),
            ),
            ast_.Assignment(
                ast_.Identifier("y"),
                ast_.Int("10"),
            ),
            ast_.Assignment(
                ast_.Identifier("z"),
                ast_.BinaryOp(
                    left=ast_.Identifier("x"),
                    right=ast_.Identifier("y"),
                    op_type=ast_.BinaryOperator.ADD,
                ),
            ),
        ]
    ),
]


TEST_AST_TYPES = list(
    map(
        mk_starting_env,  # type: ignore
        [
            {"x": ast_.BaseSimileType.Int},
            {"test_enum": ast_.EnumTypeDef({"a", "b", "c"})},
            {
                "TestStruct": ast_.StructTypeDef({"a": ast_.BaseSimileType.Int, "b": ast_.BaseSimileType.String}),
                "test_struct": ast_.StructTypeDef({"a": ast_.BaseSimileType.Int, "b": ast_.BaseSimileType.String}),
            },
            {
                "TestStruct": ast_.StructTypeDef({"a": ast_.BaseSimileType.Int, "b": ast_.BaseSimileType.String}),
                "TestStructTwo": ast_.StructTypeDef({"c": ast_.StructTypeDef({"a": ast_.BaseSimileType.Int, "b": ast_.BaseSimileType.String}), "d": ast_.BaseSimileType.String}),
                "test_struct": ast_.StructTypeDef({"c": ast_.StructTypeDef({"a": ast_.BaseSimileType.Int, "b": ast_.BaseSimileType.String}), "d": ast_.BaseSimileType.String}),
            },
            {
                "x": ast_.BaseSimileType.Int,
                "y": ast_.BaseSimileType.Int,
                "z": ast_.BaseSimileType.Int,
            },
        ],
    )
)

TEST_ASTS_WITH_TYPES = []
for ast_node, ast_type in zip(TEST_ASTS, TEST_AST_TYPES):
    typed_ast_node = deepcopy(ast_node)
    typed_ast_node = analysis.add_environments_to_ast(typed_ast_node)
    typed_ast_node._env = ast_type
    TEST_ASTS_WITH_TYPES.append((ast_node, typed_ast_node))


# def test_type_analysis(ast_node: ast_.Statements, typed_ast_node: ast_.Statements):

#     analyzed_ast = analysis.populate_ast_with_types(ast_node)
#     if analyzed_ast == typed_ast_node:
#         print("ASTs match!")
#         return

#     print("Expected:")
#     print(typed_ast_node.env)
#     print("Actual:")
#     print(analyzed_ast.env)


# for ast_node, typed_ast_node in TEST_ASTS_WITH_TYPES[-2:]:
#     test_type_analysis(ast_node, typed_ast_node)


class TestAnalysis:
    @pytest.mark.parametrize("ast_node, typed_ast_node", TEST_ASTS_WITH_TYPES)
    def test_type_analysis(self, ast_node: ast_.ASTNode, typed_ast_node: ast_.ASTNode):
        analyzed_ast = analysis.populate_ast_environments(ast_node)
        assert analyzed_ast == typed_ast_node
