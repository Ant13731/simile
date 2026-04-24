from __future__ import annotations

import textwrap

import pytest

from src.mod.data.ast_ import *
from src.mod.pipeline.parser import parse, ParseError


def normalize_source(source: str) -> str:
    return textwrap.dedent(source).strip("\n")


def start_with_body(source: str, body: ASTNode) -> Start:
    return Start(Statements([body]), source)


BASIC_EXPRESSION_CASES = [
    ("a", Identifier("a")),
    ("(a)", Identifier("a")),
    ("1", Int("1")),
    ("1.5", Float("1.5")),
    ('"hello world"', String("hello world")),
    ("True", True_()),
    ("False", False_()),
    ("not a", Not(value=Identifier("a"))),
    ("a is b", Is(Identifier("a"), Identifier("b"))),
    ("a is not b", IsNot(Identifier("a"), Identifier("b"))),
    ("a in b", In(Identifier("a"), Identifier("b"))),
    ("a not in b", NotIn(Identifier("a"), Identifier("b"))),
    ("a and b", And([Identifier("a"), Identifier("b")])),
    ("a and b and c", And([Identifier("a"), Identifier("b"), Identifier("c")])),
    ("a or b", Or([Identifier("a"), Identifier("b")])),
    ("a + b", Add(Identifier("a"), Identifier("b"))),
    ("a + b + c", Add(Add(Identifier("a"), Identifier("b")), Identifier("c"))),
    ("a - b", Subtract(Identifier("a"), Identifier("b"))),
    ("a * b", Multiply(Identifier("a"), Identifier("b"))),
    ("a / b", Divide(Identifier("a"), Identifier("b"))),
    ("a mod b", Modulo(Identifier("a"), Identifier("b"))),
    ("s ++ t", Concat(Identifier("s"), Identifier("t"))),
    ("a = b", Equal(Identifier("a"), Identifier("b"))),
    ("a != b", NotEqual(Identifier("a"), Identifier("b"))),
    ("a < b", LessThan(Identifier("a"), Identifier("b"))),
    ("a <= b", LessThanOrEqual(Identifier("a"), Identifier("b"))),
    ("a > b", GreaterThan(Identifier("a"), Identifier("b"))),
    ("a >= b", GreaterThanOrEqual(Identifier("a"), Identifier("b"))),
    ("a <<: b", Subset(Identifier("a"), Identifier("b"))),
    ("a <: b", SubsetEq(Identifier("a"), Identifier("b"))),
    ("a :>> b", Superset(Identifier("a"), Identifier("b"))),
    ("a :> b", SupersetEq(Identifier("a"), Identifier("b"))),
    ("a !<<: b", NotSubset(Identifier("a"), Identifier("b"))),
    ("a !<: b", NotSubsetEq(Identifier("a"), Identifier("b"))),
    ("a !:>> b", NotSuperset(Identifier("a"), Identifier("b"))),
    ("a !:> b", NotSupersetEq(Identifier("a"), Identifier("b"))),
    ("a ==> b", Implies(Identifier("a"), Identifier("b"))),
    ("ℙ(S)", Powerset(Identifier("S"))),
    ("powerset(S)", Powerset(Identifier("S"))),
    ("ℙ₁(S)", NonemptyPowerset(Identifier("S"))),
    ("powerset1(S)", NonemptyPowerset(Identifier("S"))),
    ("x |-> y", Maplet(Identifier("x"), Identifier("y"))),
    ("{}", SetEnumeration([])),
    ("[]", SequenceEnumeration([])),
    ("[[]]", BagEnumeration([])),
    ("{1, 2}", SetEnumeration([Int("1"), Int("2")])),
    ("{1 |-> 2}", RelationEnumeration([Maplet(Int("1"), Int("2"))])),
    ("[1, 2]", SequenceEnumeration([Int("1"), Int("2")])),
    ("[[1, 2]]", BagEnumeration([Int("1"), Int("2")])),
]

SIMPLE_STATEMENT_CASES = [
    ("return", Return(None_())),
    ("return 1", Return(Int("1"))),
    ("break", Break()),
    ("continue", Continue()),
    ("skip", Skip()),
    ("a := 1", Assignment(Identifier("a"), Int("1"), [], False)),
    ("a :: S", Assignment(Identifier("a"), Identifier("S"), [], True)),
    (
        "a: int := 1",
        Assignment(
            TypedName(Identifier("a"), Type_(Identifier("int"))),
            Int("1"),
            [],
            False,
        ),
    ),
    ('import "test_import"', Import("test_import", None_())),
    ('from "test_import" import *', Import("test_import", ImportAll())),
    ('from "test_import" import test', Import("test_import", TupleIdentifier((Identifier("test"),)))),
    (
        'from "test_import" import testA, testB',
        Import("test_import", TupleIdentifier((Identifier("testA"), Identifier("testB")))),
    ),
    (
        'from "test_import" import (testA, testB)',
        Import("test_import", TupleIdentifier((Identifier("testA"), Identifier("testB")))),
    ),
]

COMPOUND_STATEMENT_CASES = [
    (
        normalize_source(
            """
					for i in [1, 2, 3]:
						print(i)
					"""
        ),
        For(
            TupleIdentifier((Identifier("i"),)),
            SequenceEnumeration([Int("1"), Int("2"), Int("3")]),
            Statements([Call(Identifier("print"), [Identifier("i")])]),
        ),
    ),
    (
        normalize_source(
            """
					while True:
						print("Hello")
					"""
        ),
        While(
            True_(),
            Statements([Call(Identifier("print"), [String("Hello")])]),
        ),
    ),
    (
        normalize_source(
            """
					if a > b:
						print("a is greater")
					else:
						print("b is greater")
					"""
        ),
        If(
            GreaterThan(Identifier("a"), Identifier("b")),
            Statements([Call(Identifier("print"), [String("a is greater")])]),
            Else(
                Statements([Call(Identifier("print"), [String("b is greater")])]),
            ),
        ),
    ),
    (
        normalize_source(
            """
					if a > b:
						print("a")
					else if a = b:
						print("eq")
					else:
						print("b")
					"""
        ),
        If(
            GreaterThan(Identifier("a"), Identifier("b")),
            Statements([Call(Identifier("print"), [String("a")])]),
            ElseIf(
                Equal(Identifier("a"), Identifier("b")),
                Statements([Call(Identifier("print"), [String("eq")])]),
                Else(Statements([Call(Identifier("print"), [String("b")])])),
            ),
        ),
    ),
]

STRUCTURED_PROGRAM_CASES = [
    (
        """
        record A:
            a: int,
            b: str, d: int
            c: float
        """,
        RecordDef(
            Identifier("A"),
            [
                TypedName(Identifier("a"), Type_(Identifier("int"))),
                TypedName(Identifier("b"), Type_(Identifier("str"))),
                TypedName(Identifier("d"), Type_(Identifier("int"))),
                TypedName(Identifier("c"), Type_(Identifier("float"))),
            ],
        ),
    ),
    (
        """
        procedure test_func(a: int, b: str) -> bool:
            return a > 0 and b != ""
        """,
        ProcedureDef(
            Identifier("test_func"),
            [
                TypedName(Identifier("a"), Type_(Identifier("int"))),
                TypedName(Identifier("b"), Type_(Identifier("str"))),
            ],
            Statements(
                [
                    Return(
                        And(
                            [
                                GreaterThan(Identifier("a"), Int("0")),
                                NotEqual(Identifier("b"), String("")),
                            ],
                        )
                    )
                ]
            ),
            Type_(Identifier("bool")),
        ),
    ),
]

COMPREHENSION_CASES = [
    (
        "{x | x in S}",
        Quantifier(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
            expression=Identifier("x"),
            op_type=QuantifierOperator.SET,
        ),
    ),
    (
        "{x |-> y | x in X and y in Y}",
        RelationComprehension(
            predicate=And(
                [
                    In(Identifier("x"), Identifier("X")),
                    In(Identifier("y"), Identifier("Y")),
                ]
            ),
            expression=Maplet(Identifier("x"), Identifier("y")),
        ),
    ),
    (
        "[x | x in S]",
        Quantifier(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
            expression=Identifier("x"),
            op_type=QuantifierOperator.SEQUENCE,
        ),
    ),
    (
        "[[x | x in S]]",
        Quantifier(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
            expression=Identifier("x"),
            op_type=QuantifierOperator.BAG,
        ),
    ),
    (
        "⋃x · x in S | F(x)",
        UnionAll(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
            expression=Call(Identifier("F"), [Identifier("x")]),
        ),
    ),
    (
        "⋂x · x in S | F(x)",
        IntersectionAll(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
            expression=Call(Identifier("F"), [Identifier("x")]),
        ),
    ),
    (
        "lambda x . x in S | x",
        LambdaDef(
            TupleIdentifier((Identifier("x"),)),
            In(Identifier("x"), Identifier("S")),
            Identifier("x"),
        ),
    ),
]

RELATION_SUBTYPE_CASES = [
    ("A <-> B", Relation(Identifier("A"), Identifier("B"))),
    ("A <<-> B", TotalRelation(Identifier("A"), Identifier("B"))),
    ("A <->> B", SurjectiveRelation(Identifier("A"), Identifier("B"))),
    ("A <<->> B", TotalSurjectiveRelation(Identifier("A"), Identifier("B"))),
    ("A +-> B", PartialFunction(Identifier("A"), Identifier("B"))),
    ("A --> B", TotalFunction(Identifier("A"), Identifier("B"))),
    ("A >+> B", PartialInjection(Identifier("A"), Identifier("B"))),
    ("A >-> B", TotalInjection(Identifier("A"), Identifier("B"))),
    ("A +->> B", PartialSurjection(Identifier("A"), Identifier("B"))),
    ("A -->> B", TotalSurjection(Identifier("A"), Identifier("B"))),
    ("A >->> B", Bijection(Identifier("A"), Identifier("B"))),
]

SET_RELATION_OPERATION_CASES = [
    ("S \\/ T", Union(Identifier("S"), Identifier("T"))),
    ("S /\\ T", Intersection(Identifier("S"), Identifier("T"))),
    ("S \\ T", BinaryOp(Identifier("S"), Identifier("T"), BinaryOperator.DIFFERENCE)),
    ("S >< T", CartesianProduct(Identifier("S"), Identifier("T"))),
    ("R <+> S", RelationOverriding(Identifier("R"), Identifier("S"))),
    ("R ∘ S", Composition(Identifier("R"), Identifier("S"))),
    ("S <| R", BinaryOp(Identifier("S"), Identifier("R"), BinaryOperator.DOMAIN_RESTRICTION)),
    ("S <<| R", BinaryOp(Identifier("S"), Identifier("R"), BinaryOperator.DOMAIN_SUBTRACTION)),
    ("R |> S", BinaryOp(Identifier("R"), Identifier("S"), BinaryOperator.RANGE_RESTRICTION)),
    ("R |>> S", BinaryOp(Identifier("R"), Identifier("S"), BinaryOperator.RANGE_SUBTRACTION)),
]

COLLECTION_NEWLINE_CASES = [
    (
        """
        {
        }
        """,
        SetEnumeration([]),
    ),
    (
        """
        [
        ]
        """,
        SequenceEnumeration([]),
    ),
    (
        """
        [[
        ]]
        """,
        BagEnumeration([]),
    ),
    (
        """
        {
            1,
            2
        }
        """,
        SetEnumeration([Int("1"), Int("2")]),
    ),
    (
        """
        [
            1,
            2
        ]
        """,
        SequenceEnumeration([Int("1"), Int("2")]),
    ),
    (
        """
        [[
            1,
            2
        ]]
        """,
        BagEnumeration([Int("1"), Int("2")]),
    ),
    (
        """
        {
            1 |-> 2,
            3 |-> 4
        }
        """,
        RelationEnumeration(
            [
                Maplet(Int("1"), Int("2")),
                Maplet(Int("3"), Int("4")),
            ]
        ),
    ),
]

ADVANCED_EXPRESSION_CASES = [
    ("a + b * c", Add(Identifier("a"), Multiply(Identifier("b"), Identifier("c")))),
    ("(a + b) * c", Multiply(Add(Identifier("a"), Identifier("b")), Identifier("c"))),
    ("1 .. 10", BinaryOp(Int("1"), Int("10"), BinaryOperator.UPTO)),
    ("+a", Identifier("a")),
    ("-a", Negative(Identifier("a"))),
    ("a ^ b ^ c", Exponent(Identifier("a"), Exponent(Identifier("b"), Identifier("c")))),
    ("R~", Inverse(Identifier("R"))),
    ("obj.field", StructAccess(Identifier("obj"), Identifier("field"))),
    (
        "obj.field.subfield",
        StructAccess(StructAccess(Identifier("obj"), Identifier("field")), Identifier("subfield")),
    ),
    ("R[x]", Image(Identifier("R"), Identifier("x"))),
    (
        "R[x].field",
        StructAccess(Image(Identifier("R"), Identifier("x")), Identifier("field")),
    ),
    (
        "{x + 1 | x in S}",
        Quantifier(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
            expression=Add(Identifier("x"), Int("1")),
            op_type=QuantifierOperator.SET,
        ),
    ),
    (
        "a := b + c * d",
        Assignment(
            target=Identifier("a"),
            value=Add(Identifier("b"), Multiply(Identifier("c"), Identifier("d"))),
            with_clauses=[],
            choice_assignment=False,
        ),
    ),
]

ADVANCED_STATEMENT_CASES = [
    (
        normalize_source(
            """
            record Empty:
                skip
            """
        ),
        RecordDef(Identifier("Empty"), []),
    ),
    (
        normalize_source(
            """
            if a:
                skip
            else if b:
                skip
            """
        ),
        If(
            Identifier("a"),
            Statements([Skip()]),
            ElseIf(Identifier("b"), Statements([Skip()]), None_()),
        ),
    ),
    (
        normalize_source(
            """
            if a:
                skip
            else if b:
                skip
            else if c:
                skip
            else:
                skip
            """
        ),
        If(
            Identifier("a"),
            Statements([Skip()]),
            ElseIf(
                Identifier("b"),
                Statements([Skip()]),
                ElseIf(
                    Identifier("c"),
                    Statements([Skip()]),
                    Else(Statements([Skip()])),
                ),
            ),
        ),
    ),
    (
        normalize_source(
            """
            if a:
                if b:
                    skip
                else:
                    skip
            else:
                skip
            """
        ),
        If(
            Identifier("a"),
            Statements(
                [
                    If(
                        Identifier("b"),
                        Statements([Skip()]),
                        Else(Statements([Skip()])),
                    )
                ]
            ),
            Else(Statements([Skip()])),
        ),
    ),
]

QUANTIFICATION_AND_TYPING_CASES = [
    (
        "forall x . x in S",
        Forall(
            predicate=And([In(Identifier("x"), Identifier("S"))]),
        ),
    ),
    (
        "exists x . x in S and x > 0",
        Exists(
            predicate=And(
                [
                    In(Identifier("x"), Identifier("S")),
                    GreaterThan(Identifier("x"), Int("0")),
                ]
            ),
        ),
    ),
    (
        normalize_source(
            """
            record Pair:
                left: int
                right: int
            """
        ),
        RecordDef(
            Identifier("Pair"),
            [
                TypedName(Identifier("left"), Type_(Identifier("int"))),
                TypedName(Identifier("right"), Type_(Identifier("int"))),
            ],
        ),
    ),
    (
        normalize_source(
            """
            a: int := v
                with a > 0
                with a < 10
            """
        ),
        Assignment(
            target=TypedName(Identifier("a"), Type_(Identifier("int"))),
            value=Identifier("v"),
            with_clauses=[
                GreaterThan(Identifier("a"), Int("0")),
                LessThan(Identifier("a"), Int("10")),
            ],
            choice_assignment=False,
        ),
    ),
    (
        "a: S[x] := v",
        Assignment(
            target=TypedName(
                Identifier("a"),
                Type_(Type_(Identifier("S"), [Identifier("x")])),
            ),
            value=Identifier("v"),
            with_clauses=[],
            choice_assignment=False,
        ),
    ),
]

PARSER_ERROR_CASES_ASSIGNMENT_AND_TYPING = [
    (
        "a: int v",
        "Expected assignment after an expression not ending with a newline",
    ),
    (
        normalize_source(
            """
            a: int := v
                a > 0
            """
        ),
        "Each refinement line in an assignment block must start with 'with'",
    ),
]

PARSER_ERROR_CASES_CONTROL_FLOW = [
    (
        normalize_source(
            """
            if a
                skip
            """
        ),
        "Expected colon after IF condition",
    ),
    (
        normalize_source(
            """
            if a:
            skip
            """
        ),
        "Expected indentation for block",
    ),
]

PARSER_ERROR_CASES_IMPORTS = [
    (
        'from "mod" test',
        "Expected 'import' after 'from'",
    ),
    (
        'from "mod" import (a,)',
        "Expected identifier in tuple identifier",
    ),
]

PARSER_ERROR_CASES_QUANTIFICATION_AND_GROUPING = [
    (
        "forall . x in S",
        "No identifier or sub-pattern found",
    ),
    (
        "lambda x x in S | x",
        "Expected LAMBDA quantification separator",
    ),
    (
        "R[x",
        "Expected closing bracket",
    ),
    (
        "(a + b",
        "Need to close parenthesis",
    ),
]

PARSER_ERROR_CASES_STRUCTURED = [
    (
        "record A: skip",
        "Expected newline after RECORD definition",
    ),
    (
        normalize_source(
            """
            procedure f(a: int -> bool:
                skip
            """
        ),
        "Expected closing parenthesis for procedure parameters",
    ),
    (
        normalize_source(
            """
            procedure f(a: int) bool:
                skip
            """
        ),
        "Expected right arrow after procedure parameters",
    ),
]

PARSER_ERROR_CASES = (
    PARSER_ERROR_CASES_ASSIGNMENT_AND_TYPING
    + PARSER_ERROR_CASES_CONTROL_FLOW
    + PARSER_ERROR_CASES_IMPORTS
    + PARSER_ERROR_CASES_QUANTIFICATION_AND_GROUPING
    + PARSER_ERROR_CASES_STRUCTURED
)


class TestParserHappyPath:
    @pytest.mark.parametrize(
        "source, expected_body",
        BASIC_EXPRESSION_CASES,
    )
    def test_parse_basic_expressions(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        SIMPLE_STATEMENT_CASES,
    )
    def test_parse_simple_statements(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        COMPOUND_STATEMENT_CASES,
    )
    def test_parse_compound_statements(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        STRUCTURED_PROGRAM_CASES,
    )
    def test_parse_structured_programs(self, source: str, expected_body: ASTNode):
        source = normalize_source(source)
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        COMPREHENSION_CASES,
    )
    def test_parse_comprehensions(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        RELATION_SUBTYPE_CASES,
    )
    def test_parse_relation_subtypes(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        SET_RELATION_OPERATION_CASES,
    )
    def test_parse_set_and_relation_operations(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        COLLECTION_NEWLINE_CASES,
    )
    def test_parse_collections_with_newlines(self, source: str, expected_body: ASTNode):
        source = normalize_source(source)
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        ADVANCED_EXPRESSION_CASES,
    )
    def test_parse_advanced_expressions(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        ADVANCED_STATEMENT_CASES,
    )
    def test_parse_advanced_statements(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        QUANTIFICATION_AND_TYPING_CASES,
    )
    def test_parse_quantification_and_typing_forms(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)


class TestParserErrorCases:
    @pytest.mark.parametrize(
        "source, expected_error_msg",
        PARSER_ERROR_CASES,
    )
    def test_parse_error_cases(self, source: str, expected_error_msg: str):
        with pytest.raises(ParseError) as exc_info:
            parse(source)
        assert expected_error_msg in str(exc_info.value)
