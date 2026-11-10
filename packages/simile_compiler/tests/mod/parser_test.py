from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.mod.data.ast_ import *
from src.mod.pipeline.parser import parse, ParseError


def normalize_source(source: str) -> str:
    return textwrap.dedent(source).strip("\n")


def start_with_body(source: str, body: ASTNode) -> Start:
    return Start(Statements([body]), source)


def start_with_statements(source: str, body: list[ASTNode]) -> Start:
    return Start(Statements(body), source)


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
    ("ℙ(S)", Call(Identifier("ℙ"), [Identifier("S")])),
    ("powerset(S)", Call(Identifier("powerset"), [Identifier("S")])),
    ("ℙ₁(S)", Call(Identifier("ℙ₁"), [Identifier("S")])),
    ("powerset1(S)", Call(Identifier("powerset1"), [Identifier("S")])),
    ("x |-> y", Maplet(Identifier("x"), Identifier("y"))),
    ("{}", SetEnumeration([])),
    ("[]", SequenceEnumeration([])),
    ("[||]", BagEnumeration([])),
    ("{1, 2}", SetEnumeration([Int("1"), Int("2")])),
    ("{1 |-> 2}", RelationEnumeration([Maplet(Int("1"), Int("2"))])),
    ("[1, 2]", SequenceEnumeration([Int("1"), Int("2")])),
    ("[|1, 2|]", BagEnumeration([Int("1"), Int("2")])),
]

TYPE_EXPRESSION_CASES = [
    ("a: int", TypedName(Identifier("a"), Type_(Identifier("int")))),
    (
        "a: b.c",
        TypedName(
            Identifier("a"),
            Type_(
                RecordAccess(Identifier("b"), Identifier("c")),
            ),
        ),
    ),
    (
        "a: T[a,b]",
        TypedName(
            Identifier("a"),
            Type_(
                Identifier("T"),
                [Type_(Identifier("a")), Type_(Identifier("b"))],
            ),
        ),
    ),
    (
        "a: T[(a, b)]",
        TypedName(
            Identifier("a"),
            Type_(
                Identifier("T"),
                [Type_(TupleLiteral([Type_(Identifier("a")), Type_(Identifier("b"))]))],
            ),
        ),
    ),
    (
        "a: procedure[(a,), b]",
        TypedName(
            Identifier("a"),
            Type_(
                Identifier("procedure"),
                [
                    Type_(TupleLiteral([Type_(Identifier("a"))])),
                    Type_(Identifier("b")),
                ],
            ),
        ),
    ),
    (
        "a: T[T[a]]",
        TypedName(
            Identifier("a"),
            Type_(
                Identifier("T"),
                [
                    Type_(
                        Identifier("T"),
                        [Type_(Identifier("a"))],
                    ),
                ],
            ),
        ),
    ),
]

SIMPLE_STATEMENT_CASES = [
    ("return", Return(None_())),
    ("return 1", Return(Int("1"))),
    ("break", Break()),
    ("continue", Continue()),
    ("skip", Skip()),
    ("a := 1", Assignment(Identifier("a"), Int("1"), False)),
    ("a :: S", Assignment(Identifier("a"), Identifier("S"), True)),
    (
        "a: int := 1",
        Assignment(TypedName(Identifier("a"), Type_(Identifier("int"))), Int("1"), False),
    ),
    ('import "test_import"', Import(Path("test_import"), [], ImportOperator.MODULE_NAME)),
    ('from "test_import" import *', Import(Path("test_import"), [], ImportOperator.ALL_NAMES)),
    ('from "test_import" import test', Import(Path("test_import"), ["test"], ImportOperator.SPECIFIC_NAMES)),
    (
        'from "test_import" import testA, testB',
        Import(Path("test_import"), ["testA", "testB"], ImportOperator.SPECIFIC_NAMES),
    ),
    (
        'from "test_import" import (testA, testB)',
        Import(Path("test_import"), ["testA", "testB"], ImportOperator.SPECIFIC_NAMES),
    ),
]

MULTI_SIMPLE_STATEMENT_CASES = [
    (
        "a := 1; b := 2",
        [
            Assignment(Identifier("a"), Int("1"), False),
            Assignment(Identifier("b"), Int("2"), False),
        ],
    ),
    ("skip; skip", [Skip(), Skip()]),
    ('skip; import "module"', [Skip(), Import(Path("module"), [], ImportOperator.MODULE_NAME)]),
]

COMPOUND_STATEMENT_CASES = [
    (
        normalize_source("""
					for i in [1, 2, 3]:
						print(i)
					"""),
        For(
            Identifier("i"),
            SequenceEnumeration([Int("1"), Int("2"), Int("3")]),
            Statements([Call(Identifier("print"), [Identifier("i")])]),
        ),
    ),
    (
        normalize_source("""
                        for (i,j) in {(1, 2)}:
                            print(i)
                        """),
        For(
            TupleIdentifier((Identifier("i"), Identifier("j"))),
            SetEnumeration([TupleLiteral([Int("1"), Int("2")])]),
            Statements([Call(Identifier("print"), [Identifier("i")])]),
        ),
    ),
    (
        normalize_source("""
					while True:
						print("Hello")
					"""),
        While(
            True_(),
            Statements([Call(Identifier("print"), [String("Hello")])]),
        ),
    ),
    (
        normalize_source("""
					if a > b:
						print("a is greater")
					else:
						print("b is greater")
					"""),
        If(
            GreaterThan(Identifier("a"), Identifier("b")),
            Statements([Call(Identifier("print"), [String("a is greater")])]),
            Else(
                Statements([Call(Identifier("print"), [String("b is greater")])]),
            ),
        ),
    ),
    (
        normalize_source("""
					if a > b:
						print("a")
					else if a = b:
						print("eq")
					else:
						print("b")
					"""),
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
        RecordDefIdentifier(
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
        ProcedureDefIdentifier(
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
        "{x in S | x}",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("X"), True_()),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.SET,
        ),
    ),
    (
        "{x in X, y in Y | x |-> y}",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("X"), True_()),
                    Generator(Identifier("y"), Identifier("Y"), True_()),
                ],
                Maplet(Identifier("x"), Identifier("y")),
            ),
            QuantifierOperator.RELATION,
        ),
    ),
    (
        "[x in S | x]",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("S"), True_()),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.SEQUENCE,
        ),
    ),
    (
        "[|x in S | x|]",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("S"), True_()),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.BAG,
        ),
    ),
    (
        "⋃x in S | F(x)",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("S"), True_()),
                ],
                Call(Identifier("F"), [Identifier("x")]),
            ),
            QuantifierOperator.UNION_ALL,
        ),
    ),
    (
        "⋂x in S | F(x)",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("S"), True_()),
                ],
                Call(Identifier("F"), [Identifier("x")]),
            ),
            QuantifierOperator.INTERSECTION_ALL,
        ),
    ),
    (
        "lambda x .: x in S | x",
        LambdaDef(
            TupleIdentifier((Identifier("x"),)),
            In(Identifier("x"), Identifier("S")),
            Identifier("x"),
        ),
    ),
    (
        "fold i := 0 : x in S | i + x",
        Fold(
            Assignment(Identifier("i"), Int("0"), False),
            QuantifierBody(
                [Generator(Identifier("x"), Identifier("S"), True_())],
                Add(Identifier("i"), Identifier("x")),
            ),
        ),
    ),
    (
        "sum (x in S | x) ` (y in S | y)",
        Quantifier3(
            QuantifierBody(
                [],
                [
                    QuantifierBody([Generator(Identifier("x"), Identifier("S"), True_())], Identifier("x")),
                    QuantifierBody([Generator(Identifier("y"), Identifier("S"), True_())], Identifier("y")),
                ],
            ),
            QuantifierOperator.SUM,
        ),
    ),
    (
        "iter x in S : i := 0; j := 1 -> i,j | i := j + 2",
        Iter(
            IterBody(
                [
                    IterGenerator(
                        Generator(Identifier("x"), Identifier("S"), True_()),
                        [
                            Assignment(Identifier("i"), Int("0"), False),
                            Assignment(Identifier("j"), Int("1"), False),
                        ],
                    )
                ],
                IterBodyEnd(
                    Statements(
                        [
                            Assignment(
                                Identifier("i"),
                                Add(Identifier("j"), Int("2")),
                                False,
                            )
                        ]
                    ),
                    TupleIdentifier((Identifier("i"), Identifier("j"))),
                ),
            )
        ),
    ),
    (
        "iter x in S : i := 0, y in T : j := 1 -> i | i := i + j",
        Iter(
            IterBody(
                [
                    IterGenerator(
                        Generator(Identifier("x"), Identifier("S"), True_()),
                        [
                            Assignment(Identifier("i"), Int("0"), False),
                        ],
                    ),
                    IterGenerator(
                        Generator(Identifier("y"), Identifier("T"), True_()),
                        [
                            Assignment(Identifier("j"), Int("1"), False),
                        ],
                    ),
                ],
                IterBodyEnd(
                    Statements(
                        [
                            Assignment(
                                Identifier("i"),
                                Add(Identifier("i"), Identifier("j")),
                                False,
                            )
                        ]
                    ),
                    Identifier("i"),
                ),
            )
        ),
    ),
    (
        "iter (x in S : i := 0 -> i | i := x)",
        Iter(
            IterBody(
                [],
                [
                    IterBody(
                        [
                            IterGenerator(
                                Generator(Identifier("x"), Identifier("S"), True_()),
                                [
                                    Assignment(Identifier("i"), Int("0"), False),
                                ],
                            )
                        ],
                        IterBodyEnd(
                            Statements(
                                [
                                    Assignment(
                                        Identifier("i"),
                                        Identifier("x"),
                                        False,
                                    )
                                ]
                            ),
                            Identifier("i"),
                        ),
                    ),
                ],
            )
        ),
    ),
    (
        "product x in S | x",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("X"), True_()),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.PRODUCT,
        ),
    ),
    (
        "max x in S | x",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("X"), True_()),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.MAX,
        ),
    ),
    (
        "min x in S | x",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("X"), True_()),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.MIN,
        ),
    ),
    (
        normalize_source("""
            iter x in S : i := 0 -> i |
                i := x
            """),
        Iter(
            IterBody(
                [
                    IterGenerator(
                        Generator(Identifier("x"), Identifier("S"), True_()),
                        [
                            Assignment(Identifier("i"), Int("0"), False),
                        ],
                    )
                ],
                IterBodyEnd(
                    Statements(
                        [
                            Assignment(
                                Identifier("i"),
                                Identifier("x"),
                                False,
                            )
                        ]
                    ),
                    Identifier("i"),
                ),
            )
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
        [|
        |]
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
        [|
            1,
            2
        |]
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
    ("obj.field", RecordAccess(Identifier("obj"), Identifier("field"))),
    (
        "obj.field.subfield",
        RecordAccess(RecordAccess(Identifier("obj"), Identifier("field")), Identifier("subfield")),
    ),
    ("R[x]", Image(Identifier("R"), [Identifier("x")])),
    (
        "R[x].field",
        RecordAccess(Image(Identifier("R"), [Identifier("x")]), Identifier("field")),
    ),
    (
        "{x in S | x + 1}",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(Identifier("x"), Identifier("S"), True_()),
                ],
                Add(Identifier("x"), Int("1")),
            ),
            QuantifierOperator.SET,
        ),
    ),
    (
        "a := b + c * d",
        Assignment(
            target=Identifier("a"),
            value=Add(Identifier("b"), Multiply(Identifier("c"), Identifier("d"))),
            choice_assignment=False,
        ),
    ),
]

ADVANCED_STATEMENT_CASES = [
    (
        normalize_source("""
            record Empty:
                skip
            """),
        RecordDefIdentifier(Identifier("Empty"), []),
    ),
    (
        normalize_source("""
            if a:
                skip
            else if b:
                skip
            """),
        If(
            Identifier("a"),
            Statements([Skip()]),
            ElseIf(Identifier("b"), Statements([Skip()]), None_()),
        ),
    ),
    (
        normalize_source("""
            if a:
                skip
            else if b:
                skip
            else if c:
                skip
            else:
                skip
            """),
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
        normalize_source("""
            if a:
                if b:
                    skip
                else:
                    skip
            else:
                skip
            """),
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
        "forall x in S | x",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(
                        Identifier("x"),
                        Identifier("S"),
                        True_(),
                    ),
                ],
                Identifier("x"),
            ),
            QuantifierOperator.FORALL,
        ),
    ),
    (
        "exists (x,y) in S | x > 0",
        Quantifier3(
            QuantifierBody(
                [
                    Generator(
                        TupleIdentifier((Identifier("x"), Identifier("y"))),
                        Identifier("S"),
                        True_(),
                    ),
                ],
                GreaterThan(Identifier("x"), Int("0")),
            ),
            QuantifierOperator.EXISTS,
        ),
    ),
    (
        normalize_source("""
            record Pair:
                left: int
                right: int
            """),
        RecordDefIdentifier(
            Identifier("Pair"),
            [
                TypedName(Identifier("left"), Type_(Identifier("int"))),
                TypedName(Identifier("right"), Type_(Identifier("int"))),
            ],
        ),
    ),
    (
        normalize_source("""
            a: int := v
                trait a > 0
                trait a < 10
            """),
        TraitApplication(
            Assignment(
                target=TypedName(Identifier("a"), Type_(Identifier("int"))),
                value=Identifier("v"),
                choice_assignment=False,
            ),
            [
                GreaterThan(Identifier("a"), Int("0")),
                LessThan(Identifier("a"), Int("10")),
            ],
        ),
    ),
    (
        "a: S[x] := v",
        Assignment(
            target=TypedName(
                Identifier("a"),
                Type_(Identifier("S"), [Type_(Identifier("x"))]),
            ),
            value=Identifier("v"),
            choice_assignment=False,
        ),
    ),
]

PARSER_ERROR_CASES_ASSIGNMENT_AND_TYPING = [
    (
        "a: int v",
        "parsing assignment or expression (and before possible traits)",
    ),
    (
        normalize_source("""
            a: int := v
                a > 0
            """),
        "Each refinement line in an assignment block must start with 'trait'",
    ),
]

PARSER_ERROR_CASES_CONTROL_FLOW = [
    (
        normalize_source("""
            if a
                skip
            """),
        "Expected colon after IF condition",
    ),
    (
        normalize_source("""
            if a:
            skip
            """),
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
        "forall .: x in S",
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
        normalize_source("""
            procedure f(a: int -> bool:
                skip
            """),
        "Expected closing parenthesis for procedure parameters",
    ),
    (
        normalize_source("""
            procedure f(a: int) bool:
                skip
            """),
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
        TYPE_EXPRESSION_CASES,
    )
    def test_parse_type_expressions(self, source: str, expected_body: ASTNode):
        assert parse(source) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        SIMPLE_STATEMENT_CASES,
    )
    def test_parse_simple_statements(self, source: str, expected_body: ASTNode):
        assert parse(source, Path("test_source_file_path")) == start_with_body(source, expected_body)

    @pytest.mark.parametrize(
        "source, expected_body",
        MULTI_SIMPLE_STATEMENT_CASES,
    )
    def test_parse_multiple_simple_statements(self, source: str, expected_body: list[ASTNode]):
        assert parse(source, Path("test_source_file_path")) == start_with_statements(source, expected_body)

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
            parse(source, Path("test_source_file_path"))
        assert expected_error_msg in str(exc_info.value)
