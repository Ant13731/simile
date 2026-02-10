import pytest
from dataclasses import dataclass

from src import ast_


@dataclass
class TestDummyNode(ast_.ASTNode):
    pass


TEST_CONTAINS_CHILD = [
    (ast_.Identifier("a"), ast_.Identifier("a")),
    (
        ast_.BinaryOp(
            ast_.Identifier("x"),
            ast_.Identifier("y"),
            op_type=ast_.BinaryOperator.ADD,
        ),
        ast_.Identifier("x"),
    ),
    (
        ast_.IdentList([ast_.Identifier("x"), ast_.Identifier("y")]),
        ast_.Identifier("x"),
    ),
    (
        ast_.SetEnumeration(
            [
                ast_.Add(
                    ast_.Identifier("x"),
                    ast_.Identifier("y"),
                    op_type=ast_.BinaryOperator.ADD,
                ),
                ast_.Multiply(
                    ast_.Identifier("a"),
                    ast_.Identifier("b"),
                    op_type=ast_.BinaryOperator.MULTIPLY,
                ),
            ]
        ),
        ast_.Add(TestDummyNode(), TestDummyNode()),
    ),
    (
        ast_.SetEnumeration(
            [
                ast_.Add(
                    ast_.Identifier("x"),
                    ast_.Identifier("y"),
                    op_type=ast_.BinaryOperator.ADD,
                ),
                ast_.Multiply(
                    ast_.Identifier("a"),
                    ast_.Identifier("b"),
                    op_type=ast_.BinaryOperator.MULTIPLY,
                ),
            ]
        ),
        ast_.Multiply(TestDummyNode(), TestDummyNode()),
    ),
]
TEST_NOT_CONTAINS_CHILD = [
    (
        ast_.BinaryOp(
            ast_.Identifier("a"),
            ast_.Identifier("b"),
            op_type=ast_.BinaryOperator.MULTIPLY,
        ),
        ast_.BinaryOp(
            ast_.Identifier("a"),
            ast_.Identifier("b"),
            op_type=ast_.BinaryOperator.ADD,
        ),
    ),
]
TEST_CONTAINS_INSTANCES = [
    (ast_.Identifier("a"), ast_.Identifier, None, [ast_.Identifier("a")]),
    (ast_.BinaryOp(ast_.Identifier("x"), ast_.Identifier("y"), op_type=ast_.BinaryOperator.ADD), ast_.Identifier, None, [ast_.Identifier("x"), ast_.Identifier("y")]),
    (ast_.IdentList([ast_.Identifier("x"), ast_.Identifier("y")]), ast_.Identifier, None, [ast_.Identifier("x"), ast_.Identifier("y")]),
    (
        ast_.SetEnumeration(
            [
                ast_.BinaryOp(ast_.Identifier("x"), ast_.Identifier("y"), op_type=ast_.BinaryOperator.ADD),
                ast_.BinaryOp(ast_.Identifier("y"), ast_.Identifier("yx"), op_type=ast_.BinaryOperator.ADD),
                ast_.BinaryOp(ast_.Identifier("a"), ast_.Identifier("b"), op_type=ast_.BinaryOperator.MULTIPLY),
            ]
        ),
        ast_.BinaryOp,
        ast_.BinaryOperator.ADD,
        [
            ast_.BinaryOp(ast_.Identifier("x"), ast_.Identifier("y"), op_type=ast_.BinaryOperator.ADD),
            ast_.BinaryOp(ast_.Identifier("y"), ast_.Identifier("yx"), op_type=ast_.BinaryOperator.ADD),
        ],
    ),
    (
        ast_.SetEnumeration(
            [
                ast_.BinaryOp(ast_.Identifier("x"), ast_.Identifier("y"), op_type=ast_.BinaryOperator.ADD),
                ast_.BinaryOp(ast_.Identifier("a"), ast_.Identifier("b"), op_type=ast_.BinaryOperator.MULTIPLY),
            ]
        ),
        TestDummyNode,
        None,
        [],
    ),
]
TEST_CHILDREN = [
    (ast_.Identifier("a"), ["a"]),
    (
        ast_.BinaryOp(
            ast_.Identifier("x"),
            ast_.Identifier("y"),
            op_type=ast_.BinaryOperator.ADD,
        ),
        [ast_.Identifier("x"), ast_.Identifier("y"), ast_.BinaryOperator.ADD],
    ),
    (
        ast_.IdentList([ast_.Identifier("x"), ast_.Identifier("y")]),
        [ast_.Identifier("x"), ast_.Identifier("y")],
    ),
    (
        ast_.SetEnumeration(
            [
                ast_.BinaryOp(
                    ast_.Identifier("x"),
                    ast_.Identifier("y"),
                    op_type=ast_.BinaryOperator.ADD,
                ),
                ast_.BinaryOp(
                    ast_.Identifier("a"),
                    ast_.Identifier("b"),
                    op_type=ast_.BinaryOperator.MULTIPLY,
                ),
            ]
        ),
        [
            ast_.BinaryOp(
                ast_.Identifier("x"),
                ast_.Identifier("y"),
                op_type=ast_.BinaryOperator.ADD,
            ),
            ast_.BinaryOp(
                ast_.Identifier("a"),
                ast_.Identifier("b"),
                op_type=ast_.BinaryOperator.MULTIPLY,
            ),
            ast_.CollectionOperator.SET,
        ],
    ),
]
TEST_LEAF_NODES = [
    ast_.Identifier("a"),
    ast_.Int("42"),
]
TEST_NOT_LEAF_NODES = [
    ast_.BinaryOp(
        ast_.Identifier("x"),
        ast_.Identifier("y"),
        op_type=ast_.BinaryOperator.ADD,
    ),
    ast_.IdentList([ast_.Identifier("x"), ast_.Identifier("y")]),
    ast_.SetEnumeration(
        [
            ast_.BinaryOp(
                ast_.Identifier("x"),
                ast_.Identifier("y"),
                op_type=ast_.BinaryOperator.ADD,
            ),
            ast_.BinaryOp(
                ast_.Identifier("a"),
                ast_.Identifier("b"),
                op_type=ast_.BinaryOperator.MULTIPLY,
            ),
        ]
    ),
]


class TestASTNode:
    @pytest.mark.parametrize("ast_node", map(lambda x: x[0], TEST_CONTAINS_CHILD))
    def test_contains_self(self, ast_node: ast_.ASTNode):
        # Test if the ASTNode contains itself
        args = [ast_node.__class__]
        if hasattr(ast_node, "op_type"):
            args.append(ast_node.op_type)
        assert ast_node.contains(*args)  # type: ignore

    @pytest.mark.parametrize("ast_node, contains", TEST_CONTAINS_CHILD)
    def test_contains_child(self, ast_node: ast_.ASTNode, contains: ast_.ASTNode):
        # Test if the ASTNode contains a specific child node type
        args = [contains.__class__]
        if hasattr(contains, "op_type"):
            args.append(contains.op_type)
        assert ast_node.contains(*args)  # type: ignore

    @pytest.mark.parametrize("ast_node, not_contains", TEST_NOT_CONTAINS_CHILD)
    def test_contains_not_child(self, ast_node: ast_.ASTNode, not_contains: type[ast_.ASTNode]):
        # Test if the ASTNode does not contain a specific child node type
        args = [not_contains.__class__]
        if hasattr(not_contains, "op_type"):
            args.append(not_contains.op_type)
        assert not ast_node.contains(*args)  # type: ignore

    @pytest.mark.parametrize("ast_node, instance, with_op_type, expected_instances", TEST_CONTAINS_INSTANCES)
    def test_find_all_instances(
        self,
        ast_node: ast_.ASTNode,
        instance: type[ast_.ASTNode],
        with_op_type: ast_.Operators | None,
        expected_instances: list[ast_.ASTNode],
    ):
        # Test if the ASTNode finds all instances of a specific type

        assert ast_node.find_all_instances(instance, with_op_type) == expected_instances

    @pytest.mark.parametrize("ast_node, expected_children", TEST_CHILDREN)
    def test_list_children(self, ast_node: ast_.ASTNode, expected_children: list[ast_.ASTNode]):
        # Test if the ASTNode lists all children
        assert list(ast_node.children()) == expected_children

    @pytest.mark.parametrize("ast_node", TEST_LEAF_NODES)
    def test_is_leaf(self, ast_node: ast_.ASTNode):
        # Test if the ASTNode is a leaf node
        assert ast_node.is_leaf()

    @pytest.mark.parametrize("ast_node", TEST_NOT_LEAF_NODES)
    def test_is_not_leaf(self, ast_node: ast_.ASTNode):
        # Test if the ASTNode is not a leaf node
        assert not ast_node.is_leaf()
