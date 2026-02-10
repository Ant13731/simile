import pytest
from loguru import logger

from src.mod.ast_ import *
from src.mod.parser import parse
from src.mod.analysis import populate_ast_environments
from src.mod.optimizer import (
    collection_optimizer,
    REWRITE_COLLECTION,
    SyntacticSugarForBags,
    BuiltinFunctions,
    ComprehensionConstructionCollection,
    DisjunctiveNormalFormCollection,
    OrWrappingCollection,
    GeneratorSelectionCollection,
    GSPToLoopsCollection,
    LoopsCodeGenerationCollection,
    ReplaceAndSimplifyCollection,
)

EXPECTED_STRUCTURE_TEST = [
    (
        "card({1, 2})",
        """
c := 0
for e in {1, 2}:
    c := c + 1
""",
    ),
    (
        "card({1, 2} \\/ {2, 3})",
        """
c := 0
for e in {1, 2}:
    c := c + 1
for e in {2, 3}:
    if not (e in {1, 2}):
        c := c + 1
""",
    ),
    (
        "card({s · s in {1, 2} | s})",
        """
c := 0
for e in {1, 2}:
    c := c + 1
""",
    ),
    (
        "card({s · s in {1, 2} or s in {2, 3}| s})",
        """
c := 0
for e in {1, 2}:
    c := c + 1
for e in {2, 3}:
    if not(e in {1, 2}):
        c := c + 1
""",
    ),
    (
        "card({s · s in {1, 2} and s != 1 or s in {2, 3} and s = 3 | s})",
        """
c := 0
for e in {1, 2}:
    if e != 1:
        c := c + 1
for e in {2, 3}:
    if e = 3 and not(e in {1, 2} and e != 1):
        c := c + 1
""",
    ),
    (
        "card({s · s in {1, 2} and (s != 1 or s != 0) or s in {2, 3} and s = 3 | s})",
        """
c := 0
for e in {1, 2}:
    if e != 1 or e != 0:
        c := c + 1
for e in {2, 3}:
    if e = 3 and not(e in {1, 2} and (e != 1 or e != 0)):
        c := c + 1
""",
    ),
    (
        "card({s · s in { x + 1 | x in {1, 2} or x in {4}} or s in { x + 2 | x in {2, 3}} | s})",
        """
c := 0

     """,
    ),
    (
        "card({s,t · s in {1, 2} and t == s + 1 or s in {2, 3} and t == s + 2 | t } and s = 3)",
        """
c := 0

     """,
    ),
    (
        "card({s | s in {1, 2}})",
        """c := 0
for e in {1, 2}:
    c := c + 1
""",
    ),
    (
        "card({s | s in {1, 2} or s in {2, 3}})",
        """
c := 0
for e in {1, 2}:
    c := c + 1
for e in {2, 3}:
    if not(e in {1, 2}):
        c := c + 1
""",
    ),
    (
        "{s | s in {1, 2}}",
        """c := {}
for e in {1, 2}:
    c := c + 1
""",
    ),
    (
        "{s | s in {1, 2} or s in {2, 3}}",
        """
c := {}
for e in {1, 2}:
    c = insert(c, e)
for e in {2, 3}:
    if not(e in {1, 2}):
        c = insert(c, e)
""",
    ),
    (
        """
S := {1,2}
T := {1}
S := S ∪ T
""",
        """
S := {1, 2}
T := {1}

c := {}
for e in {1, 2}:
    c = insert(c, e)
for e in {2, 3}:
    if not(e in {1, 2}):
        c = insert(c, e)
S := c
""",
    ),
    (
        """
S := {1,2}
T := {1}
S := S ∩ T
""",
        """
S := {1, 2}
T := {1}

c := {}
for e in {1, 2}:
    if e in {1}:
        c = insert(c, e)

""",
    ),
]
# TEST_SET_COMPREHENSION = [
#     (
#         Union(
#             SetEnumeration(
#                 [
#                     Int("1"),
#                     Int("1"),
#                     Int("2"),
#                 ]
#             ),
#             SetEnumeration(
#                 [
#                     Int("2"),
#                     Int("3"),
#                     Int("4"),
#                 ]
#             ),
#         ),
#     ),
#     (
#         Union(
#             SetEnumeration(
#                 [
#                     Int("1"),
#                     Int("1"),
#                     Int("2"),
#                 ]
#             ),
#             SetEnumeration(
#                 [
#                     Int("2"),
#                 ]
#             ),
#         ),
#     ),
#     (
#         Union(
#             SetEnumeration(
#                 [
#                     Int("1"),
#                     Int("1"),
#                     Int("2"),
#                 ]
#             ),
#             SetComprehension(
#                 And(
#                     [
#                         In(
#                             Identifier("x"),
#                             SetEnumeration(
#                                 [
#                                     Int("2"),
#                                 ]
#                             ),
#                         ),
#                     ],
#                 ),
#                 Identifier("x"),
#             ),
#         ),
#     ),
# ]

# vars = """
# a = True
# b = False
# c = b
# d = a
# """
# prepend = [
#     Assignment(Identifier("a"), True_()),
#     Assignment(Identifier("b"), True_()),
#     Assignment(Identifier("c"), Identifier("a")),
#     Assignment(Identifier("d"), Identifier("a")),
# ]
# TEST_DNF = list(
#     map(
#         lambda i: (vars + i[0], Statements(prepend + [i[1]])),
#         [
#             ("a and b or c and d",),
#             ("not a and b or c and (d or (a and (b or c)))",),
#         ],
#     )
# )
# TEST_GEN_SEL = [
#     (
#         SetComprehension(
#             And(
#                 [
#                     In(
#                         Identifier("x"),
#                         SetEnumeration(
#                             [
#                                 Int("1"),
#                                 Int("2"),
#                             ],
#                         ),
#                     )
#                 ]
#             ),
#             Identifier("x"),
#         ),
#     ),
#     (
#         SetComprehension(
#             And(
#                 [
#                     In(
#                         Identifier("x"),
#                         SetEnumeration(
#                             [
#                                 Int("1"),
#                                 Int("2"),
#                             ],
#                         ),
#                     ),
#                     Equal(
#                         Add(
#                             Identifier("x"),
#                             Int("1"),
#                         ),
#                         Identifier("y"),
#                     ),
#                 ]
#             ),
#             Identifier("y"),
#             7,
#         ),
#     ),
# ]
# TEST_CODE_GEN = [
#     (),
# ]

OPTIMIZED_STRUCTURE_TEST = EXPECTED_STRUCTURE_TEST + [
    ("{1, 2} ∪ {2, 3}", "{s | s in {1, 2} ∪ {2, 3}}"),
    ("{1, 2} ∪ {2, 3}", "{s | s in {1, 2} or s in {2, 3}}"),
    ("card({1, 2} ∪ {2, 3})", "card({s | s in {1, 2} or s in {2, 3}})"),
]


class TestRewritingSets:

    @pytest.mark.parametrize("input, expected", EXPECTED_STRUCTURE_TEST)
    def test_against_expected_structure(self, input: str, expected: str):
        parsed_input = parse(input)
        assert not isinstance(parsed_input, list), f"Parser should not be throwing errors..., input {input} got {parsed_input}"

        parsed_expected_input = parse(expected)
        assert not isinstance(parsed_expected_input, list), f"Parser should not be throwing errors..., input {expected} got {parsed_expected_input}"

        analyzed_input = populate_ast_environments(parsed_input)
        actual = collection_optimizer(analyzed_input, SET_REWRITE_COLLECTION)

        logger.debug(f"Actual:\n{actual.pretty_print_algorithmic()}")

        assert structurally_equal(actual, parsed_expected_input)

    @pytest.mark.parametrize("input, expected", EXPECTED_STRUCTURE_TEST)
    def test_optimized_structures_match(self, input: str, expected: str):
        parsed_input = parse(input)
        assert not isinstance(parsed_input, list), f"Parser should not be throwing errors..., input {input} got {parsed_input}"

        parsed_expected_input = parse(expected)
        assert not isinstance(parsed_expected_input, list), f"Parser should not be throwing errors..., input {expected} got {parsed_expected_input}"

        analyzed_input = populate_ast_environments(parsed_input)
        actual = collection_optimizer(analyzed_input, SET_REWRITE_COLLECTION)
        logger.debug(f"Actual: {actual.pretty_print_algorithmic()}")

        analyzed_expected = populate_ast_environments(parsed_expected_input)
        actual_expected = collection_optimizer(analyzed_expected, SET_REWRITE_COLLECTION)
        logger.debug(f"Actual Expected: {actual_expected.pretty_print_algorithmic()}")
        assert structurally_equal(actual, actual_expected)

    # @pytest.mark.parametrize("input, expected", TEST_SET_COMPREHENSION)
    # def test_set_comprehension_collection(self, input: ASTNode, expected: ASTNode):
    #     analyzed_input = populate_ast_environments(input)
    #     actual = collection_optimizer(analyzed_input, [SetComprehensionConstructionCollection])
    #     assert actual == expected

    # @pytest.mark.parametrize("input, expected", TEST_DNF)
    # def test_disjunctive_normal_form_quantifier_predicate_collection(self, input: ASTNode, expected: ASTNode):
    #     analyzed_input = populate_ast_environments(input)
    #     actual = collection_optimizer(analyzed_input, [DisjunctiveNormalFormQuantifierPredicateCollection])
    #     assert actual == expected

    # @pytest.mark.parametrize("input, expected", TEST_GEN_SEL)
    # def test_generator_selection_collection(self, input: ASTNode, expected: ASTNode):
    #     analyzed_input = populate_ast_environments(input)
    #     actual = collection_optimizer(analyzed_input, [GeneratorSelectionCollection])
    #     assert hasattr(actual, "_selected_generators")
    #     assert actual._selected_generators == expected

    # @pytest.mark.parametrize("input, expected", TEST_CODE_GEN)
    # def test_set_code_generation_collection(self, input: ASTNode, expected: ASTNode):
    #     analyzed_input = populate_ast_environments(input)
    #     actual = collection_optimizer(analyzed_input, [SetCodeGenerationCollection])
    #     assert actual == expected
