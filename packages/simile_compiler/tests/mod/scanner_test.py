import pytest
import hypothesis

from src.mod.scanner import (
    scan,
    OPERATOR_TOKEN_TABLE,
    KEYWORD_TABLE,
    TokenType,
    Token,
    Location,
    ScanningException,
    ScannerException,
)


# MARK: Setup
TOKENS_AND_KEYWORDS = list(OPERATOR_TOKEN_TABLE.items()) + list(KEYWORD_TABLE.items())
KEYWORDS_WITH_SPACE = list(filter(lambda item: " " in item, KEYWORD_TABLE.keys()))


def get_token_types(input_: str) -> list[TokenType]:
    return list(map(lambda tk: tk.type_, scan(input_)))


def assert_language_invariants(tokens: list[TokenType]):
    assert tokens.count(TokenType.INDENT) == tokens.count(TokenType.DEDENT)
    if tokens:
        assert tokens[0] != TokenType.EOF
        assert tokens[-1] == TokenType.EOF


def assert_token_types_equal(actual: list[TokenType], expected: list[TokenType]):
    assert len(actual) == len(expected)
    for actual_token, expected_type in zip(actual, expected):
        assert actual_token == expected_type


def assert_tokens_equal(actual: list[Token], expected: list[Token]):
    assert len(actual) == len(expected)
    for actual_token, expected_token in zip(actual, expected):
        assert actual_token == expected_token
        assert actual_token.type_ == expected_token.type_
        assert actual_token.value == expected_token.value
        assert actual_token.start_location == expected_token.start_location
        assert actual_token.end_location == expected_token.end_location


# MARK: Happy path
@pytest.mark.parametrize(
    "input_, expected",
    TOKENS_AND_KEYWORDS,
)
def test_single_symbol(input_: str, expected: TokenType):
    expected_tokens = [expected, TokenType.NEWLINE, TokenType.EOF]
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected_tokens)


@pytest.mark.parametrize(
    "input_fst, expected_fst",
    TOKENS_AND_KEYWORDS,
)
@pytest.mark.parametrize(
    "input_snd, expected_snd",
    TOKENS_AND_KEYWORDS,
)
def test_double_symbols_with_space(
    input_fst: str,
    expected_fst: TokenType,
    input_snd: str,
    expected_snd: TokenType,
):
    input_ = f"{input_fst} {input_snd}"
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)

    expected = [expected_fst, expected_snd, TokenType.NEWLINE, TokenType.EOF]
    if input_ in KEYWORDS_WITH_SPACE:
        # if the input is a keyword with an optional space,
        # only expect one keyword
        expected = [KEYWORD_TABLE[input_], TokenType.NEWLINE, TokenType.EOF]

    # special case for "is not in" since "is not" and "not in" are also keywords
    if input_ == "is not in":
        expected = [TokenType.IS_NOT, TokenType.IN, TokenType.NEWLINE, TokenType.EOF]

    assert_token_types_equal(actual_tokens, expected)


@pytest.mark.parametrize(
    "input_, expected",
    [
        ("\n", []),
        ("", []),
        (" ", []),
        (" \n", []),
        ("\t\n\t", []),
        ("\t", []),
    ],
)
def test_ignore_whitespace(input_: str, expected: list[TokenType]):
    actual_tokens = get_token_types(input_)
    # assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected + [TokenType.EOF])


@pytest.mark.parametrize(
    "input_, expected",
    [
        ("< .", [TokenType.LT, TokenType.DOT, TokenType.NEWLINE]),
        (
            " < .",
            [
                TokenType.INDENT,
                TokenType.LT,
                TokenType.DOT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
        (
            "  < .",
            [
                TokenType.INDENT,
                TokenType.LT,
                TokenType.DOT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
        (
            "   < .",
            [
                TokenType.INDENT,
                TokenType.LT,
                TokenType.DOT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
        (
            "    < .",
            [
                TokenType.INDENT,
                TokenType.LT,
                TokenType.DOT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
        (
            "\t< .",
            [
                TokenType.INDENT,
                TokenType.LT,
                TokenType.DOT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
        (
            "<\n\t<\n<",
            [
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.INDENT,
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
                TokenType.LT,
                TokenType.NEWLINE,
            ],
        ),
        (
            "<\n <\n<",
            [
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.INDENT,
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
                TokenType.LT,
                TokenType.NEWLINE,
            ],
        ),
        (
            "<\n <\n  <\n",
            [
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.INDENT,
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.INDENT,
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
                TokenType.DEDENT,
            ],
        ),
        (
            "<\n <\n  <\n<",
            [
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.INDENT,
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.INDENT,
                TokenType.LT,
                TokenType.NEWLINE,
                TokenType.DEDENT,
                TokenType.DEDENT,
                TokenType.LT,
                TokenType.NEWLINE,
            ],
        ),
    ],
)
def test_indentation(input_: str, expected: list[TokenType]):
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected + [TokenType.EOF])


@pytest.mark.parametrize(
    "input_, expected",
    [
        ("test", [TokenType.IDENTIFIER, TokenType.NEWLINE]),
        ("\ttest", [TokenType.INDENT, TokenType.IDENTIFIER, TokenType.NEWLINE, TokenType.DEDENT]),
        ("test: int", [TokenType.IDENTIFIER, TokenType.COLON, TokenType.IDENTIFIER, TokenType.NEWLINE]),
        (
            "test: int1\ntest:int2",
            [
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.NEWLINE,
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.NEWLINE,
            ],
        ),
        (
            "\ttest: int1\n\ttest:int2",
            [
                TokenType.INDENT,
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.NEWLINE,
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
    ],
)
def test_identifiers(input_: str, expected: list[TokenType]):
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected + [TokenType.EOF])


@pytest.mark.parametrize(
    "input_, expected",
    [
        (
            """
record A:
    a: int,
    b: str, d: int
    c: float
""",
            [
                TokenType.RECORD,
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.NEWLINE,
                TokenType.INDENT,
                #
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.COMMA,
                TokenType.NEWLINE,
                #
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.COMMA,
                #
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.NEWLINE,
                #
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.IDENTIFIER,
                TokenType.NEWLINE,
                TokenType.DEDENT,
            ],
        ),
    ],
)
def test_struct_definition(input_: str, expected: list[TokenType]):
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected + [TokenType.EOF])


@pytest.mark.parametrize(
    "input_, expected",
    [
        (
            "{1, 2} \\/ {2, 3}",
            [
                TokenType.L_BRACE,
                TokenType.INTEGER,
                TokenType.COMMA,
                TokenType.INTEGER,
                TokenType.R_BRACE,
                #
                TokenType.UNION,
                #
                TokenType.L_BRACE,
                TokenType.INTEGER,
                TokenType.COMMA,
                TokenType.INTEGER,
                TokenType.R_BRACE,
                TokenType.NEWLINE,
            ],
        ),
    ],
)
def test_expression(input_: str, expected: list[TokenType]):
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected + [TokenType.EOF])


@pytest.mark.parametrize(
    "input_, expected",
    [
        (
            "# this is a comment 123 \\/",
            [
                TokenType.COMMENT,
            ],
        ),
    ],
)
def test_comment(input_: str, expected: list[TokenType]):
    actual_tokens = get_token_types(input_)
    assert_language_invariants(actual_tokens)
    assert_token_types_equal(actual_tokens, expected + [TokenType.EOF])


@pytest.mark.parametrize(
    "input_, expected",
    [
        (
            " test",
            [
                Token(TokenType.INDENT, "", Location(0, 0), Location(0, 1)),
                Token(TokenType.IDENTIFIER, "test", Location(0, 1), Location(0, 5)),
                Token(TokenType.NEWLINE, "", Location(0, 5), Location(0, 6)),
                Token(TokenType.DEDENT, "", Location(0, 5), Location(1, 0)),
                Token(TokenType.EOF, "", Location(0, 5), Location(1, 0)),
            ],
        ),
    ],
)
def test_tokens_manual(input_: str, expected: list[Token]):
    res = scan(input_)
    assert_tokens_equal(res, expected)


@pytest.mark.parametrize(
    "input_, expected",
    [
        ('"hello world"', [TokenType.STRING, TokenType.NEWLINE, TokenType.EOF]),
        ('"hello \\ world"', [TokenType.STRING, TokenType.NEWLINE, TokenType.EOF]),
        ('"hello \n world"', [TokenType.STRING, TokenType.NEWLINE, TokenType.EOF]),
        ("123", [TokenType.INTEGER, TokenType.NEWLINE, TokenType.EOF]),
        ("123.456", [TokenType.FLOAT, TokenType.NEWLINE, TokenType.EOF]),
    ],
)
def test_literal(input_: str, expected: list[TokenType]):
    actual = get_token_types(input_)
    assert_language_invariants(actual)
    assert_token_types_equal(actual, expected)


# MARK: Negative path
@pytest.mark.parametrize(
    "input_",
    [
        '"unterminated string',
        "'unterminated string\n100",
        "'unterminated string\\",
    ],
)
def test_unterminated_string(input_: str):
    with pytest.raises(ScannerException):
        scan(input_)


@pytest.mark.parametrize(
    "input_",
    [
        "  1\n 2",
        " 1\n\t2",
    ],
)
def test_malformed_indentation(input_: str):
    with pytest.raises(ScannerException):
        scan(input_)


def test_operator_prefix_without_exact_match_raises(monkeypatch):
    import src.mod.scanner.scanner as scanner_module
    from src.mod.scanner import TokenType, scan, ScannerException

    # Make "=<" a valid prefix (because "=<x" exists) but not a full token.
    monkeypatch.setattr(
        scanner_module,
        "OPERATOR_TOKEN_TABLE",
        {
            "=": TokenType.EQUALS,
            "=<x": TokenType.IMPLIES,
        },
    )

    with pytest.raises(ScannerException) as exc:
        scan("=<")

    assert "Cannot find symbol =< in operator token table" in str(exc.value)
