from dataclasses import dataclass, field
import copy

from src.mod.scanner.tokens import (
    TokenType,
    OPERATOR_TOKEN_TABLE,
    KEYWORD_TABLE,
)


class ScanException(Exception):
    pass


@dataclass
class Location:
    """Represents the location of a token in the source code."""

    line: int
    column: int

    def __str__(self):
        return f"line {self.line}, column {self.column}"


@dataclass
class Token:
    """Represents a single token in the Simile language."""

    type_: TokenType
    value: str
    start_location: Location
    end_location: Location

    def __repr__(self) -> str:
        if self.value and self.value.lower() != self.type_.name.lower():
            return f"{self.type_.name}({self.value})"
        return self.type_.name

    def length(self) -> int:
        """Returns the length of the token in characters."""
        return self.end_location.column - self.start_location.column + 1

    def multiline(self) -> bool:
        """Checks if the token spans multiple lines."""
        return self.start_location.line != self.end_location.line


@dataclass
class Scanner:
    """Scanner methods and state. This class should not be initialized directly, but used through the :func:`scan` function."""

    text: str
    """Source code/input text to scan."""

    current_index_lexeme_start: int = 0
    """Pointer for the start of the currently examined token."""
    current_index: int = 0
    """Pointer for the currently examined character."""

    current_location_lexeme_start: Location = field(default_factory=lambda: Location(0, 0))
    """:attr:`current_index_lexeme_start` in Line/Column format (for better error messages)."""
    current_location: Location = field(default_factory=lambda: Location(0, 0))
    """:attr:`current_index` in Line/Column format (for better error messages)."""

    indentation_stack: list[str] = field(default_factory=list)
    """Stack of indentation levels. Each level is a string of whitespace characters that represent the indentation level.

    Whitespace is significant, so we need to keep track of the indentation levels."""

    scanned_tokens: list[Token] = field(default_factory=list)
    """Return value of the scanner. Contains all tokens scanned from the text.

    We store this in an object to catch as many errors as possible through one run."""

    ignore_newline: bool = True
    """State marker for the scanner - when true, do not generate newline tokens when scanning"""

    @property
    def max_location(self) -> Location:
        """Returns the maximum location in the text."""
        return Location(len(self.text.splitlines()), len(self.text.splitlines()[-1]) if self.text else 0)

    @property
    def at_end_of_text(self) -> bool:
        """Checks if the scanner has reached the end of the text."""
        return self.current_index >= len(self.text)

    @property
    def current_lexeme_len(self) -> int:
        """Returns the length of the current lexeme being scanned."""
        return self.current_index - self.current_index_lexeme_start

    def peek(self, offset: int = 0) -> str | None:
        """Peek at the next character without consuming it. Offset is used as a lookahead."""
        if self.at_end_of_text:
            return None
        return self.text[self.current_index + offset]

    def advance(self) -> str:
        """Consume and return one character."""
        c = self.text[self.current_index]
        self.current_index += 1
        self.current_location.column += 1
        return c

    def match(self, expected: str) -> bool:
        """Consume the next character if it matches the expected character (only one character at a time may be matched)."""
        assert len(expected) == 1, "Only one character of matching is allowed at a time."
        if self.at_end_of_text:
            return False
        if self.peek() != expected:
            return False
        self.advance()
        return True

    def match_phrase(self, expected: str, expect_whitespace_or_eof_after_phrase: bool = False) -> bool:
        """Repeatedly call :meth:`~self.match` until the expected string is completely matched.

        Upon matching failure, this will backtrack character indices to the beginning of the phrase."""
        start_location = self.current_location
        start_current = self.current_index

        expected_index = 0
        while expected_index < len(expected) and self.match(expected[expected_index]):
            expected_index += 1

        if expected_index == len(expected):
            if not expect_whitespace_or_eof_after_phrase:
                return True
            next_char = self.peek()
            if next_char is None or next_char.isspace():
                return True

        # Backtrack to the start of the phrase
        self.current_location = start_location
        self.current_index = start_current
        return False

    def add_token(self, type_: TokenType, value: str = "") -> None:
        """Adds a token to the scanner's output.

        Args:
            type_: The type of the token.
            value: The value of the token. Defaults to an empty string.
        """

        self.scanned_tokens.append(Token(type_, value, copy.deepcopy(self.current_location_lexeme_start), copy.deepcopy(self.current_location)))

    def indentation(self) -> None:  # type: ignore
        # Handle indentation at the start of a line
        self.ignore_newline = True
        c = self.peek()
        if c is None:
            return  # End of file (this should be unreachable)

        # Match existing indentation as much as possible
        matched_up_to_index = 0
        for indent_str in self.indentation_stack:
            if not self.match_phrase(indent_str):
                break
            matched_up_to_index += 1
            # c = self.text[self.current_index - 1]  # If theres indentation, we're safe to look back one character

        c = self.peek()
        # Indentation doesn't match but no content on line - ignore indentation for line
        if c is None or c in "\n#":
            return

        indentation_difference = matched_up_to_index - len(self.indentation_stack)

        if indentation_difference < 0:
            if self.peek() == " " or self.peek() == "\t":
                # There is more "indentation" left to consume, but the leftover does not match what we expect so far.
                raise ScanException(
                    self.current_location,
                    self.peek(),
                    f"Indentation does not match. Expected {self.indentation_stack[indentation_difference:]} but got {self.move_until_no_whitespace()}",
                )
            # Next character is another token with less indentation, so record all required dedents
            self.indentation_stack = self.indentation_stack[:indentation_difference]
            for _ in range(-indentation_difference):
                self.add_token(TokenType.DEDENT)
            return

        # we've matched up to the indentation point
        if c not in " \t":
            # Maintain indentation level (do nothing; continue)
            return

        # Add new indentation level
        new_indent = self.move_until_no_whitespace()
        # ignore new indentation on blank/comment/EOF lines, also ignore if we didn't indent at all
        c = self.peek()
        if c is None or c in "\n#":
            return
        self.indentation_stack.append(new_indent)
        self.add_token(TokenType.INDENT)

    def scan_next(self) -> None:
        """Scans the next token from the text.

        This method will update the scanner's state and add tokens to the scanned_tokens list."""

        # End of file check
        if self.peek() is None:
            return

        if self.current_location.column == 0:
            # Handle indentation at the start of a line
            self.indentation()
            # If we moved the pointer to the next lexeme, we need to update the starting pointer (done outside of this function)
            if self.current_location.column != 0:
                return

        c = self.advance()

        # # Handle indentation
        # # If we are at the start of a line...
        # if self.current_location.column == 1:
        #     self.ignore_newline = True
        #     # Match existing indentation as much as possible
        #     matched_up_to_index = 0
        #     for indent_str in self.indentation_stack:
        #         if not self.match_phrase(indent_str):
        #             break
        #         matched_up_to_index += 1
        #         c = self.text[self.current_index - 1]  # If theres indentation, we're safe to look back one character

        #     # Indentation doesn't match but no content on line - ignore indentation for line
        #     if c in "\n#":
        #         return

        #     indentation_difference = matched_up_to_index - len(self.indentation_stack)

        #     if indentation_difference < 0:
        #         if self.peek() == " " or self.peek() == "\t":
        #             # There is more "indentation" left to consume, but the leftover does not match what we expect so far.
        #             raise ScanException(
        #                 self.current_location,
        #                 self.peek(),
        #                 f"Indentation does not match. Expected {self.indentation_stack[indentation_difference:]} but got {self.move_until_no_whitespace()}",
        #             )
        #         # Next character is another token with less indentation, so record all required dedents
        #         self.indentation_stack = self.indentation_stack[:indentation_difference]
        #         for _ in range(-indentation_difference):
        #             self.add_token(TokenType.DEDENT)
        #     else:  # we've matched up to the indentation point
        #         if c in " \t":  # and (self.peek() == " " or self.peek() == "\t"):
        #             # Add new indentation level
        #             new_indent = c + self.move_until_no_whitespace()
        #             # ignore new indentation on blank/comment/EOF lines, also ignore if we didn't indent at all
        #             if self.peek() == "\n" or self.peek() == "#" or self.peek() is None:  # or new_indent == "":
        #                 return
        #             self.indentation_stack.append(new_indent)
        #             self.add_token(TokenType.INDENT)
        #         # Maintain indentation level (do nothing; continue)

        match c:
            case "\n":
                if not self.ignore_newline:
                    self.add_token(TokenType.NEWLINE)
                self.current_location.line += 1
                self.current_location.column = 0
                return
            case "\r":
                return
            case " " | "\t":
                # self.current_location.column will never be equal to 1 here (covered above)
                return
            # Comment
            case "#":
                while not self.at_end_of_text and self.peek() != "\n":
                    self.advance()
                value = self.text[self.current_index_lexeme_start + 1 : self.current_index]
                self.add_token(TokenType.COMMENT, value)
            # Primitives
            case '"':  # includes multiline?
                self.ignore_newline = False
                while self.peek() != '"' and not self.at_end_of_text:
                    if self.peek() == "\n":
                        self.current_location.line += 1
                        self.current_location.column = 0
                    if self.peek() == "\\":
                        self.advance()
                    self.advance()

                if self.at_end_of_text:
                    raise ScanException(self.current_location, self.peek(), f'Unterminated string literal (expected ", found {self.peek()})')
                self.advance()  # will match \"
                value = self.text[self.current_index_lexeme_start + 1 : self.current_index - 1]
                self.add_token(TokenType.STRING, value)
            case _ if c.isdigit() or c == "." and (peek := self.peek()) is not None and peek.isdigit():
                self.ignore_newline = False
                while (peek := self.peek()) is not None and peek.isdigit():
                    self.advance()
                if self.peek() == "." and (peek := self.peek(1)) is not None and (peek.isdigit() or peek.isspace()):
                    self.advance()
                while (peek := self.peek()) is not None and peek.isdigit():
                    self.advance()
                value = self.text[self.current_index_lexeme_start : self.current_index]
                if "." in value:
                    self.add_token(TokenType.FLOAT, value)
                else:
                    self.add_token(TokenType.INTEGER, value)
            # Operators
            case _ if c in {k[0] for k in OPERATOR_TOKEN_TABLE}:
                self.ignore_newline = False

                consumed_characters = c
                possible_tokens: dict[str, TokenType] = {k: v for (k, v) in OPERATOR_TOKEN_TABLE.items() if k.startswith(consumed_characters)}
                # prev_possible_tokens = OPERATOR_TOKEN_TABLE

                # Eliminate possible tokens until the dictionary is empty
                while True:
                    peek = self.peek()
                    if peek is None:
                        break
                    peek_possible_tokens = {k: v for k, v in OPERATOR_TOKEN_TABLE.items() if len(k) > len(consumed_characters) and k.startswith(consumed_characters + peek)}
                    if len(peek_possible_tokens) == 0:
                        break
                    consumed_characters += self.advance()
                    possible_tokens = {k: v for (k, v) in OPERATOR_TOKEN_TABLE.items() if k.startswith(consumed_characters)}

                # while len(possible_tokens) > 0:
                #     prev_possible_tokens = possible_tokens
                #     peek = self.peek()
                #     if peek is None:
                #         break
                #     possible_tokens = {k: v for k, v in OPERATOR_TOKEN_TABLE.items() if len(k) > len(consumed_characters) and k.startswith(consumed_characters + peek)}
                #     consumed_characters += self.advance()

                # If token is valid, the previous iteration of possible tokens should contain the exact token we are looking for
                # if len(possible_tokens) < 1:
                #     raise ScanException(
                #         self.location,
                #         self.peek(),
                #         f"Symbol {consumed_characters} has multiple possible matches in the table {possible_tokens}, but none were valid with the next character {self.peek()}",
                #     )
                if possible_tokens.get(consumed_characters) is None:
                    raise ScanException(
                        self.current_location,
                        self.peek(),
                        f"Cannot find symbol {consumed_characters} in operator token table. Possible matches are {possible_tokens}, but none were valid with the next character {self.peek()}",
                    )

                self.add_token(OPERATOR_TOKEN_TABLE[consumed_characters], consumed_characters)
            case _ if c.isalpha() or c == "_":
                self.ignore_newline = False
                while True:
                    c_ = self.peek()
                    if c_ is None:
                        break
                    if not (c_.isalnum() or c_ == "_"):
                        break
                    self.advance()
                value = self.text[self.current_index_lexeme_start : self.current_index]
                token_type = KEYWORD_TABLE.get(value, TokenType.IDENTIFIER)

                if token_type == TokenType.IS:
                    if self.match_phrase(" not", True):
                        token_type = TokenType.IS_NOT
                elif token_type == TokenType.NOT:
                    if self.match_phrase(" in", True):
                        token_type = TokenType.NOT_IN
                self.add_token(token_type, value)
            case _:
                raise ScanException(self.current_location, self.peek(), "Unexpected character")

    def move_to_next_whitespace(self) -> None:
        """Advances the scanner past the next whitespace character in the text."""
        while not self.at_end_of_text:
            char = self.advance()
            if char.isspace():
                return None

    def move_until_no_whitespace(self) -> str:
        """Advances the scanner until it reaches a non-whitespace character.

        NOTE: This does not include newlines (in which case we can just ignore the entire blank line)"""
        moved_characters = ""
        while (c := self.peek()) is not None and c.isspace() and c != "\n":
            moved_characters += self.advance()
        return moved_characters


# TODO good error handling. need to catch as many errors as possible and return them instead of tokens
def scan(text: str) -> list[Token]:
    """Converts Simile source code into a list of tokens.

    Args:
        text (str): Simile source code (may be multiline)

    Returns:
        list[Token]: A list of tokens extracted from the source code
    """
    assert isinstance(text, str), "Input text must be a string"
    if not text.endswith("\n"):
        text += "\n"

    scanner = Scanner(text)

    while not scanner.at_end_of_text:
        try:
            scanner.current_index_lexeme_start = scanner.current_index
            scanner.current_location_lexeme_start.line = scanner.current_location.line
            scanner.current_location_lexeme_start.column = scanner.current_location.column
            scanner.scan_next()
        except ScanException as e:
            print(f"Error at {scanner.current_location}: {e}")
            scanner.move_to_next_whitespace()

    # Cleanup indentation, eof
    if scanner.indentation_stack:
        for _ in scanner.indentation_stack:
            scanner.add_token(TokenType.DEDENT)
        scanner.indentation_stack.clear()
    scanner.add_token(TokenType.EOF)
    return scanner.scanned_tokens
