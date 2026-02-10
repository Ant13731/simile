import pytest

from src.mod.scanner import (
    scan,
    OPERATOR_TOKEN_TABLE,
    KEYWORD_TABLE,
    TokenType,
    Token,
    Location,
)


TOKENS_AND_KEYWORDS = list(OPERATOR_TOKEN_TABLE.items()) + list(KEYWORD_TABLE.items())
TOKENS_AND_KEYWORDS_NO_NOT = list(
    filter(
        lambda item: item[1]
        not in [
            TokenType.NOT,
            TokenType.NOT_IN,
            TokenType.IS_NOT,
        ],
        TOKENS_AND_KEYWORDS,
    )
)


class TestSymbols:
    @pytest.mark.parametrize(
        "input_1, expected_1",
        TOKENS_AND_KEYWORDS,
    )
    def test_single_symbol(self, input_1: str, expected_1: TokenType):
        assert list(map(lambda tk: tk.type_, scan(input_1))) == [expected_1, TokenType.EOF]

    # @pytest.mark.parametrize(
    #     "input_1, expected_1",
    #     TOKENS_AND_KEYWORDS_NO_NOT,
    # )
    # @pytest.mark.parametrize(
    #     "input_2, expected_2",
    #     TOKENS_AND_KEYWORDS_NO_NOT,
    # )
    # def test_double_symbols_with_space(self, input_1: str, input_2: str, expected_1: TokenType, expected_2: TokenType):
    #     input_ = input_1 + " " + input_2
    #     assert list(map(lambda tk: tk.type_, scan(input_))) == [expected_1, expected_2, TokenType.EOF]

    @pytest.mark.parametrize(
        "input_1, expected_1",
        [
            ("\n", []),
            ("", []),
            (" ", []),
            (" \n", []),
            ("\t\n\t", []),
            ("\t", []),
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
            (
                """
struct A:
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
    def test_manual(self, input_1: str, expected_1: list[TokenType]):
        res = list(map(lambda tk: tk.type_, scan(input_1)))
        assert res == expected_1 + [TokenType.EOF]
        assert res.count(TokenType.INDENT) == res.count(TokenType.DEDENT)

    @pytest.mark.parametrize(
        "input_1, expected_1",
        [
            (
                " test",
                [
                    Token(TokenType.INDENT, "", Location(0, 0), Location(0, 1)),
                    Token(TokenType.IDENTIFIER, "test", Location(0, 1), Location(0, 5)),
                    Token(TokenType.NEWLINE, "", Location(0, 5), Location(1, 0)),
                    Token(TokenType.DEDENT, "", Location(1, 0), Location(1, 0)),
                    Token(TokenType.EOF, "", Location(1, 0), Location(1, 0)),
                ],
            ),
        ],
    )
    def test_tokens_manual(self, input_1: str, expected_1: list[Token]):
        res = scan(input_1)
        assert list(map(lambda t: t.type_, res)) == list(map(lambda t: t.type_, expected_1))
        assert list(map(lambda t: t.value, res)) == list(map(lambda t: t.value, expected_1))
