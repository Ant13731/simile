from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, ClassVar, Any, NoReturn, TypeVar, Mapping
import inspect
from functools import wraps

from colorama import just_fix_windows_console
from termcolor import colored
from loguru import logger


from src.mod.pipeline.scanner import Token, TokenType, scan, TOKENS_THAT_CAN_ACT_AS_TYPE_IDENTIFIERS, TOKENS_THAT_CAN_ACT_AS_FUNC_IDENTIFIERS
from src.mod.data import ast_

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")
WHITESPACE_TOKENS = {TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT}

just_fix_windows_console()


@dataclass
class ParseErr:
    """Class to represent a parser error."""

    message: str
    token: Token
    token_index: int
    offending_line: str
    derivation: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        ret = ""
        ret += f"Error occurred on line {self.token.start_location.line}:"
        ret += f"\n{self.offending_line}\n"

        ret += " " * self.token.start_location.column
        if self.token.multiline():
            ret += colored("^...", "red")
        else:
            ret += colored("^" * (self.token.length() - 1), "red")

        ret += f"\nParseError for token {self.token} at parser index {self.token_index}:"
        ret += f"\n - {"\n - ".join(self.message.splitlines())}"
        ret += "\nDerivation: " + " -> ".join(self.derivation)
        return ret


class ParseException(Exception):
    """Used to enter panic mode (and should be recovered through the parser)"""

    pass


class ParseError(Exception):
    """Raised with all parse errors formatted as clear stdout output"""

    def __init__(self, parser: Parser):
        err_str = f"Failed to parse input, found {len(parser.errors)} error(s).\n"
        for err in parser.errors:
            err_str += f"{err}\n"

        err_str += "\nParser info:\n"
        err_str += f"Tokens: {len(parser.tokens)}\n"
        err_str += f"Errors: {len(parser.errors)}\n"
        err_str += f"Current index: {parser.current_index}\n"
        # Tried to limit the number of tokens to relevant areas, but doesnt really work
        # pre_tokens = ", ".join(list(map(str, parser.tokens[parser.current_index - 6 : parser.current_index - 1])))
        # cur_token = colored(parser.tokens[parser.current_index], "green")
        # post_tokens = ", ".join(list(map(str, parser.tokens[parser.current_index + 1 : parser.current_index + 6])))
        # err_str += f"Surrounding input tokens: {pre_tokens}, {cur_token}, {post_tokens}\n"
        # For debug
        err_str += f"Input tokens: {parser.tokens}\n"

        super().__init__(err_str)
        self.parser = parser

    pass


def store_derivation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to store the derivation of the parse tree as a state in the parser."""

    @wraps(func)
    def wrapper(self: Parser, *args, **kwargs) -> Any:
        self.derivation.append(func.__name__)
        res = func(self, *args, **kwargs)
        self.derivation = self.derivation[:-1]  # Remove the last entry after the function call
        return res

    return wrapper


@dataclass
class Parser:
    """Parser class to handle parsing of tokens into an AST."""

    tokens: list[Token]
    original_text: str  # Used only for error messages
    source_file_path: Path | None
    current_index: int = 0
    errors: list[ParseErr] = field(default_factory=list)
    derivation: list[str] = field(default_factory=list)

    # Idea: store the first sets and the corresponding functions (that would otherwise be "matched" when making decisions)
    # It may be nice to allow for nested first sets and then a lookup (using the idea of getting all leaves from a tree...)

    # Idea 2: store a mapping of production names -> first sets. first sets may include references to other productions
    # (ie. using strings instead of TokenTypes)
    first_sets: ClassVar[dict[str, set[str | TokenType]]] = {
        "start": {TokenType.EOF, "statements"},
        "statements": {"simple_statements", "compound_stmt"},
        "simple_statements": {"assignment_or_expr", "control_flow_stmt", "import_stmt"},
        "simple_stmt": {"assignment_or_expr", "control_flow_stmt", "import_stmt"},
        "assignment_or_expr": {"expr"},
        "trait_stmt": {TokenType.INDENT},
        "expr": {"quantification", "predicate"},
        "quantification": {
            TokenType.LAMBDA,
            TokenType.GENERAL_UNION,
            TokenType.GENERAL_INTERSECTION,
            TokenType.FORALL,
            TokenType.EXISTS,
            TokenType.PRODUCT,
            TokenType.SUM,
            TokenType.FOLD,
            TokenType.ITER,
            TokenType.MAX,
            TokenType.MIN,
        },
        "quantification_body": {"branch_quantification_body", "generator"},
        "branch_quantification_body": {TokenType.L_PAREN},
        "generator": {"ident_list"},
        "iter_quantification_body": {"branch_iter_quantification_body", "generator_with_assignments"},
        "branch_iter_quantification_body": {TokenType.L_PAREN},
        "generator_with_assignments": {"generator"},
        "assignment": {"expr"},
        "iter_block": {"simple_stmt", TokenType.NEWLINE},
        "ident_list": {"ident_list_item"},
        "ident_list_item": {TokenType.IDENTIFIER, TokenType.L_PAREN},
        "predicate": {"implication"},
        "implication": {"disjunction"},
        "disjunction": {"conjunction"},
        "conjunction": {"negation"},
        "negation": {TokenType.NOT, "atom_bool"},
        "atom_bool": {"pair_expr"},
        "pair_expr": {"rel_set_expr"},
        "rel_set_expr": {"set_expr"},
        "set_expr": {"interval_expr"},
        "rel_sub_expr": {TokenType.SET_DIFFERENCE, TokenType.RANGE_RESTRICTION, TokenType.RANGE_SUBTRACTION},
        "interval_expr": {"arithmetic_expr"},
        "arithmetic_expr": {"term"},
        "term": {"factor"},
        "factor": {TokenType.PLUS, TokenType.MINUS, "power"},
        "power": {"primary"},
        "primary": {"atom"},
        "atom_follow": {TokenType.DOT, TokenType.L_BRACKET, TokenType.L_PAREN},
        "atom": {
            TokenType.INTEGER,
            TokenType.FLOAT,
            TokenType.STRING,
            TokenType.TRUE,
            TokenType.FALSE,
            # TokenType.NONE,
            TokenType.IDENTIFIER,
            "set",
            "sequence",
            "bag",
            "tuple",
            TokenType.L_PAREN,
        },
        "set": {TokenType.L_BRACE},
        "bag": {TokenType.L_DOUBLE_BRACKET},
        "sequence": {TokenType.L_BRACKET},
        "tuple": {TokenType.L_PAREN},
        "collection_body": {"quantification_body", "enumeration_body"},
        "enumeration_body": {TokenType.NEWLINE, "expr"},
        "compound_stmt": {
            "if_stmt",
            "for_stmt",
            "while_stmt",
            "record_stmt",
            "procedure_stmt",
        },
        "if_stmt": {TokenType.IF},
        "else_stmt": {TokenType.ELSE},
        "for_stmt": {TokenType.FOR},
        "while_stmt": {TokenType.WHILE},
        "record_stmt": {TokenType.RECORD},
        "procedure_stmt": {TokenType.PROCEDURE},
        "block": {"simple_statements", TokenType.INDENT},
        "typed_name": {TokenType.IDENTIFIER},
        "type_expr": {
            TokenType.IDENTIFIER,
            TokenType.L_PAREN,
            *TOKENS_THAT_CAN_ACT_AS_TYPE_IDENTIFIERS,
        },
        "tuple_type_expr_body": {"type_expr"},
        "control_flow_stmt": {TokenType.RETURN, TokenType.BREAK, TokenType.CONTINUE, TokenType.SKIP},
        "import_stmt": {TokenType.IMPORT, TokenType.FROM},
        "import_list": {TokenType.MULT, "flat_tuple_identifier"},
        "flat_tuple_identifier": {TokenType.IDENTIFIER, TokenType.L_PAREN},
        "ident_list_item_non_maplet": {TokenType.IDENTIFIER, TokenType.L_PAREN},
    }

    @classmethod
    def get_first_set(cls, production_name: str) -> set[TokenType]:
        first_set = set()
        for elem in cls.first_sets[production_name]:
            if isinstance(elem, str):
                first_set |= cls.get_first_set(elem)
            else:
                first_set.add(elem)
        return first_set

    @property
    def eof(self) -> bool:
        return self.peek().type_ == TokenType.EOF

    ignore_whitespace_: bool = False

    def peek(self, offset: int = 0) -> Token:
        if True:
            # FIXME Whitespace skipping code is broken
            # if not self.ignore_whitespace_:
            return self.tokens[self.current_index + offset]

        current_token = self.tokens[self.current_index + offset]
        while self.current_index + offset < len(self.tokens) and current_token.type_ in WHITESPACE_TOKENS:
            self.current_index += 1
            current_token = self.tokens[self.current_index + offset]
        return current_token

    def advance(self) -> Token:
        """Advance to the next token."""
        if not self.eof:
            self.current_index += 1
        return self.peek(-1)

    def check(self, token_type: TokenType) -> bool:
        return not self.eof and self.peek().type_ == token_type

    def match(self, token_type: TokenType) -> bool:
        if self.check(token_type):
            self.advance()
            return True
        return False

    def consume(self, token_type: TokenType, msg: str) -> None:
        if not self.match(token_type):
            self.error(msg, expected_override_msg=f"Expected {token_type}, got {self.peek().type_}", level_offset=1)

    def error(self, msg: str, expected_override_msg: str = "", level_offset: int = 0) -> NoReturn:
        current_token = self.peek()
        msg_2 = expected_override_msg
        if not msg_2:
            msg_2 = f"Expected one of {self.get_first_set(inspect.stack()[1 + level_offset].function)}"
        self.errors.append(
            ParseErr(
                msg + f"\n{msg_2}",  # \nError originated from {inspect.stack()[1 + level_offset].function}"
                current_token,
                self.current_index,
                self.original_text.splitlines()[current_token.start_location.line],
                self.derivation,
            )
        )
        raise ParseException("Parse error - this error should be caught within the parser (otherwise, see self.errors)")

    def synchronize(self) -> None:
        """Skip tokens until we reach a token that can start a new statement."""
        self.ignore_whitespace_ = False
        first_set = self.get_first_set("compound_stmt")
        while not self.eof:
            if self.peek().type_ in first_set or self.peek().type_ == TokenType.NEWLINE:
                self.derivation = []
                return
            self.advance()

    def left_associative_optional_parse(
        self,
        func: Callable[[], A],
        tokens_and_types: Mapping[TokenType, Callable[[A | B, A], B]],
        default_left: A | None = None,
    ) -> A | B:
        left: A | B | None = default_left
        if left is None:
            left = func()

        while (t := self.peek()).type_ in tokens_and_types:
            self.advance()  # TODO check this?
            left = tokens_and_types[t.type_](left, func())
        return left

    def ignore_whitespace(self, set_to: bool) -> bool:
        set_value_back_to = self.ignore_whitespace_
        self.ignore_whitespace_ = set_to
        return set_value_back_to

    # Parsing based (loosely) on the grammar in the specification
    @store_derivation
    def start(self) -> ast_.Start:
        if not self.tokens or self.eof:
            return ast_.Start(ast_.None_(), self.original_text)
        statements = self.statements()
        try:
            if not self.eof and self.peek().type_ != TokenType.NEWLINE and self.peek(1).type_ != TokenType.EOF:
                self.error(f"Unexpected token(s) after parsing statements (all tokens should be consumed by this point). Leftover tokens: {self.tokens[self.current_index :]}")
        except ParseException:
            pass
        return ast_.Start(statements, self.original_text)

    @store_derivation
    def statements(self) -> ast_.Statements:
        statements = []
        statements_first_set = self.get_first_set("statements")
        while self.peek().type_ in statements_first_set:
            try:
                if self.match(TokenType.COMMENT):
                    continue

                if self.peek().type_ in self.get_first_set("simple_statements"):
                    simple_statements = self.simple_statements()
                    statements.extend(simple_statements.items)
                elif self.peek().type_ in self.get_first_set("compound_stmt"):
                    statements.append(self.compound_stmt())
                else:
                    self.error("Unexpected statement starter")
            except ParseException:
                self.synchronize()

        return ast_.Statements(statements)

    @store_derivation
    def simple_statements(self) -> ast_.Statements:
        if self.peek().type_ in self.get_first_set("assignment_or_expr"):
            assignment_or_expr = self.assignment_or_expr()
            if self.peek().type_ == TokenType.SEMICOLON:
                statements = self.simple_statements_continuation()
                return ast_.Statements([assignment_or_expr] + statements)
            self.consume(TokenType.NEWLINE, "Expected NEWLINE after parsing assignment or expression (and before possible traits)")
            if self.peek().type_ in self.get_first_set("trait_stmt"):
                trait_stmts = self.trait_stmt()
                return ast_.Statements([ast_.TraitApplication(target=assignment_or_expr, traits=trait_stmts)])
            return ast_.Statements([assignment_or_expr])
        elif self.peek().type_ in self.get_first_set("control_flow_stmt"):
            control_flow_stmt = self.control_flow_stmt()
            statements = self.simple_statements_continuation()
            return ast_.Statements([control_flow_stmt] + statements)
        elif self.peek().type_ in self.get_first_set("import_stmt"):
            import_stmt = self.import_stmt()
            statements = self.simple_statements_continuation()
            return ast_.Statements([import_stmt] + statements)
        else:
            self.error("Unexpected statement starter")

    @store_derivation
    def simple_statements_continuation(self) -> list[ast_.ASTNode]:
        statements = []
        while self.match(TokenType.SEMICOLON):
            statements.append(self.simple_stmt())
        self.consume(TokenType.NEWLINE, "Expected end of simple statements continuation")
        return statements

    @store_derivation
    def trait_stmt(self) -> list[ast_.ASTNode]:
        self.consume(TokenType.INDENT, "Expected indent after assignment or expression newline before trait statement")
        with_clauses = []
        while not self.match(TokenType.DEDENT):
            self.consume(TokenType.TRAIT, "Each refinement line in an assignment block must start with 'trait'")
            with_clauses.append(self.expr())
            self.consume(TokenType.NEWLINE, "Expected newline after with clause expression")
        return with_clauses

    @store_derivation
    def simple_stmt(self) -> ast_.SimpleStmt | ast_.ASTNode:
        t = self.peek()
        if t.type_ in self.get_first_set("assignment_or_expr"):
            return self.assignment_or_expr()
        if t.type_ in self.get_first_set("control_flow_stmt"):
            return self.control_flow_stmt()
        if t.type_ in self.get_first_set("import_stmt"):
            return self.import_stmt()
        self.error("Invalid start to simple_stmt")

    @store_derivation
    def assignment_or_expr(self) -> ast_.ASTNode:
        expr = self.expr()
        if self.peek().type_ not in [TokenType.COLON, TokenType.ASSIGN, TokenType.CHOICE_ASSIGN]:
            return expr

        # now in assignment rule - could either see a type annotation or not
        if self.match(TokenType.COLON):
            type_ = self.type_expr()
            expr = ast_.TypedName(expr, type_)

        if self.peek().type_ not in [TokenType.ASSIGN, TokenType.CHOICE_ASSIGN]:
            return expr  # can type an expression without making it an assignment

        match self.advance().type_:
            case TokenType.CHOICE_ASSIGN:
                choice_assignment = True
            case TokenType.ASSIGN:
                choice_assignment = False
            case _:
                self.error("Unexpected token after type annotation in assignment or expr rule")

        value = self.expr()
        return ast_.Assignment(target=expr, value=value, choice_assignment=choice_assignment)

    @store_derivation
    def assignment(self) -> ast_.Assignment:
        expr = self.expr()

        # now in assignment rule - could either see a type annotation or not
        if self.match(TokenType.COLON):
            type_ = self.type_expr()
            expr = ast_.TypedName(expr, type_)

        match self.advance().type_:
            case TokenType.CHOICE_ASSIGN:
                choice_assignment = True
            case TokenType.ASSIGN:
                choice_assignment = False
            case _:
                self.error("Expected assignment symbol after type annotation or expression in assignment rule")

        # Since first of assignment and expr are shared, check if next token is an assignment
        value = self.expr()
        return ast_.Assignment(target=expr, value=value, choice_assignment=choice_assignment)

    @store_derivation
    def type_expr(self) -> ast_.Type_:
        t = self.advance()
        if t.type_ in {TokenType.IDENTIFIER, *TOKENS_THAT_CAN_ACT_AS_TYPE_IDENTIFIERS}:
            base: ast_.ASTNode = ast_.Identifier(t.value)

            while self.match(TokenType.DOT):
                t = self.advance()
                if t.type_ not in {TokenType.IDENTIFIER, *TOKENS_THAT_CAN_ACT_AS_TYPE_IDENTIFIERS}:
                    self.error("Expected identifier after '.' in type expression")
                base = ast_.RecordAccess(base, ast_.Identifier(t.value))

            if not self.match(TokenType.L_BRACKET):
                return ast_.Type_(base)
            set_whitespace_back_to = self.ignore_whitespace(True)

            generic_parameters: list[ast_.ASTNode] = [self.type_expr()]
            while self.match(TokenType.COMMA):
                generic_parameters.append(self.type_expr())

            # FIXME: Horrible hack but the scanner parses double r brackets as bag notation
            ending_token = self.peek()
            if ending_token.type_ == TokenType.R_DOUBLE_BRACKET:
                ending_token.type_ = TokenType.R_BRACKET
            else:
                self.consume(TokenType.R_BRACKET, "Expected closing bracket when parsing generic type parameters")
            self.ignore_whitespace(set_whitespace_back_to)
            return ast_.Type_(base, generic_parameters)

        if t.type_ == TokenType.L_PAREN:
            set_whitespace_back_to = self.ignore_whitespace(True)
            if self.match(TokenType.R_PAREN):
                self.ignore_whitespace(set_whitespace_back_to)
                return ast_.Type_(ast_.None_())

            types: list[ast_.ASTNode] = [self.type_expr()]
            self.consume(TokenType.COMMA, "Expected comma when parsing tuple type (required even for single tuple types)")
            if self.peek().type_ in self.get_first_set("type_expr"):
                types.append(self.type_expr())
                while self.match(TokenType.COMMA):
                    types.append(self.type_expr())
            self.consume(TokenType.R_PAREN, "Expected closing parenthesis when parsing generic type parameters")
            self.ignore_whitespace(set_whitespace_back_to)
            return ast_.Type_(ast_.TupleLiteral(types))

        self.error("Unexpected token when parsing type_expr (not a tuple or identifier)")

    @store_derivation
    def predicate(self) -> ast_.Predicate | ast_.ASTNode:
        return self.left_associative_optional_parse(
            self.implication,
            {
                TokenType.EQUIVALENT: ast_.Equivalent,
                TokenType.NOT_EQUIVALENT: ast_.NotEquivalent,
            },
        )

    @store_derivation
    def ident_list(self) -> ast_.IdentifierListTypes:
        ident_list_items = [self.ident_list_item()]
        while self.match(TokenType.COMMA):
            ident_list_items.append(self.ident_list_item())
        # Dont needlessly wrap in tupleIdentifiers
        if len(ident_list_items) == 1:
            return ident_list_items[0]
        return ast_.TupleIdentifier(tuple(ident_list_items))

    @store_derivation
    def ident_list_item(self) -> ast_.IdentifierListTypes:
        return self.left_associative_optional_parse(
            self.ident_list_item_non_maplet,
            {
                TokenType.MAPLET: ast_.TupleIdentifier.from_maplet,
            },
        )

    @store_derivation
    def ident_list_item_non_maplet(self) -> ast_.IdentifierListTypes:
        match (t := self.advance()).type_:
            case TokenType.IDENTIFIER:
                item: ast_.IdentifierListTypes = ast_.Identifier(t.value)
            case TokenType.L_PAREN:
                set_whitespace_back_to = self.ignore_whitespace(True)
                self.advance()
                item = self.ident_list()
                self.consume(TokenType.R_PAREN, "Expected end to identifier item sub-list")
                self.ignore_whitespace(set_whitespace_back_to)
            case _:
                self.error("No identifier or sub-pattern found")
        return item

    @store_derivation
    def implication(self) -> ast_.ASTNode:
        disjunction = self.disjunction()
        while (t := self.peek()).type_ in [TokenType.IMPLIES]:
            self.advance()
            match t.type_:
                case TokenType.IMPLIES:
                    disjunction = ast_.Implies(disjunction, self.disjunction())
                # case TokenType.REV_IMPLIES:
                #     disjunction = ast_.RevImplies(disjunction, self.implication())
                case _:
                    self.error("Unreachable state")
        return disjunction

    @store_derivation
    def disjunction(self) -> ast_.ASTNode:
        conjunctions = [self.conjunction()]
        while self.match(TokenType.OR):
            conjunctions.append(self.conjunction())
        if len(conjunctions) == 1:
            return conjunctions[0]
        return ast_.Or(conjunctions)

    @store_derivation
    def conjunction(self) -> ast_.ASTNode:
        negation = [self.negation()]
        while self.match(TokenType.AND):
            negation.append(self.negation())
        if len(negation) == 1:
            return negation[0]
        return ast_.And(negation)

    @store_derivation
    def negation(self) -> ast_.ASTNode:
        if self.match(TokenType.NOT):
            return ast_.Not(self.negation())
        return self.atom_bool()

    @store_derivation
    def atom_bool(self) -> ast_.ASTNode:
        pair_expr = self.pair_expr()
        match self.peek().type_:
            case TokenType.EQUALS:
                bin_op: type[ast_.BinaryOp] = ast_.Equal
            case TokenType.NOT_EQUALS:
                bin_op = ast_.NotEqual
            case TokenType.IS:
                bin_op = ast_.Is
            case TokenType.IS_NOT:
                bin_op = ast_.IsNot
            case TokenType.LT:
                bin_op = ast_.LessThan
            case TokenType.GT:
                bin_op = ast_.GreaterThan
            case TokenType.LE:
                bin_op = ast_.LessThanOrEqual
            case TokenType.GE:
                bin_op = ast_.GreaterThanOrEqual
            case TokenType.IN:
                bin_op = ast_.In
            case TokenType.NOT_IN:
                bin_op = ast_.NotIn
            case TokenType.SUBSET:
                bin_op = ast_.Subset
            case TokenType.SUBSET_EQ:
                bin_op = ast_.SubsetEq
            case TokenType.SUPERSET:
                bin_op = ast_.Superset
            case TokenType.SUPERSET_EQ:
                bin_op = ast_.SupersetEq
            case TokenType.NOT_SUBSET:
                bin_op = ast_.NotSubset
            case TokenType.NOT_SUBSET_EQ:
                bin_op = ast_.NotSubsetEq
            case TokenType.NOT_SUPERSET:
                bin_op = ast_.NotSuperset
            case TokenType.NOT_SUPERSET_EQ:
                bin_op = ast_.NotSupersetEq
            case _:
                return pair_expr  # Since comparison is optional, we can return immediately if no comp op matches
        self.advance()
        right = self.pair_expr()
        return bin_op(pair_expr, right)  # type: ignore # TODO fix type?

    @store_derivation
    def expr(self) -> ast_.ASTNode:
        t = self.peek()
        if t.type_ in self.get_first_set("quantification"):
            return self.quantification()
        if t.type_ in self.get_first_set("predicate"):
            return self.predicate()
        # if t.type_ in self.get_first_set("pair_expr"):
        # return self.pair_expr()
        self.error("Invalid start to expr")

    @store_derivation
    def quantification(self) -> ast_.ASTNode:
        t = self.advance()
        match t.type_:
            case TokenType.LAMBDA:
                params = ast_.TupleIdentifier(())
                if self.peek().type_ not in (TokenType.DOT, TokenType.CDOT):
                    params = self.flat_tuple_identifier()

                if not self.match(TokenType.DOT):
                    self.consume(TokenType.CDOT, "Expected LAMBDA quantification separator")
                predicate = self.predicate()
                self.consume(TokenType.VBAR, "Expected LAMBDA quantification predicate separator")
                return ast_.LambdaDef(params, predicate, self.expr())
            case TokenType.FOLD:
                initializing_assignment = self.assignment()
                self.consume(TokenType.COLON, "Expected FOLD quantification separator `:' between generator and initializing assignment")
                body = self.quantification_body()
                return ast_.Fold(initializing_assignment, body)
            case TokenType.ITER:
                return ast_.Iter(self.iter_quantification_body())
            case _ if t.type_ in {
                TokenType.GENERAL_UNION,
                TokenType.GENERAL_INTERSECTION,
                TokenType.FORALL,
                TokenType.EXISTS,
                TokenType.SUM,
                TokenType.PRODUCT,
                TokenType.MAX,
                TokenType.MIN,
            }:
                op_type: ast_.QuantifierOperator | None = None
                match t.type_:
                    case TokenType.GENERAL_UNION:
                        op_type = ast_.QuantifierOperator.UNION_ALL
                    case TokenType.GENERAL_INTERSECTION:
                        op_type = ast_.QuantifierOperator.INTERSECTION_ALL
                    case TokenType.FORALL:
                        op_type = ast_.QuantifierOperator.FORALL
                    case TokenType.EXISTS:
                        op_type = ast_.QuantifierOperator.EXISTS
                    case TokenType.SUM:
                        op_type = ast_.QuantifierOperator.SUM
                    case TokenType.PRODUCT:
                        op_type = ast_.QuantifierOperator.PRODUCT
                    case TokenType.MAX:
                        op_type = ast_.QuantifierOperator.MAX
                    case TokenType.MIN:
                        op_type = ast_.QuantifierOperator.MIN
                assert op_type is not None, "op_type should have been defined in above mapping"
                body = self.quantification_body()
                return ast_.Quantifier3(body, op_type)
            case _:
                self.error("Invalid start to quantification")

    @store_derivation
    def quantification_body(self) -> ast_.QuantifierBody:
        if self.peek().type_ in self.get_first_set("branch_quantification_body"):
            return ast_.QuantifierBody([], self.branch_quantification_body())
        generators = [self.generator()]
        while self.match(TokenType.COMMA):
            if self.peek().type_ in self.get_first_set("branch_quantification_body"):
                return ast_.QuantifierBody(generators, self.branch_quantification_body())
            generators.append(self.generator())
        self.consume(TokenType.VBAR, "Expected pipe symbol after generators in quantification body")
        expr = self.expr()
        return ast_.QuantifierBody(generators, expr)

    @store_derivation
    def branch_quantification_body(self) -> list[ast_.QuantifierBody]:
        self.consume(TokenType.L_PAREN, "Expected opening parenthesis for branch_quantification_body")
        set_whitespace_back_to = self.ignore_whitespace(True)
        quantifier_bodies: list[ast_.QuantifierBody] = [self.quantification_body()]
        self.consume(TokenType.R_PAREN, "Expected closing parenthesis for branch_quantification_body")
        self.ignore_whitespace(set_whitespace_back_to)
        while self.match(TokenType.BACKTICK):
            self.consume(TokenType.L_PAREN, "Expected opening parenthesis for branch_quantification_body")
            set_whitespace_back_to = self.ignore_whitespace(True)
            quantifier_bodies.append(self.quantification_body())
            self.consume(TokenType.R_PAREN, "Expected closing parenthesis for branch_quantification_body")
            self.ignore_whitespace(set_whitespace_back_to)
        return quantifier_bodies

    @store_derivation
    def iter_quantification_body(self) -> ast_.IterBody:
        if self.peek().type_ in self.get_first_set("branch_iter_quantification_body"):
            return ast_.IterBody([], self.branch_iter_quantification_body())
        generators = [self.generator_with_assignments()]
        while self.match(TokenType.COMMA):
            if self.peek().type_ in self.get_first_set("branch_iter_quantification_body"):
                return ast_.IterBody(generators, self.branch_iter_quantification_body())
            generators.append(self.generator_with_assignments())
        self.consume(TokenType.RIGHTARROW, "Expected right arrow with return values after iter quantification generators")
        return_list = self.ident_list()
        self.consume(TokenType.VBAR, "Expected pipe symbol after return values in iter quantification")
        body = self.iter_block()
        return ast_.IterBody(generators, ast_.IterBodyEnd(body, return_list))

    @store_derivation
    def branch_iter_quantification_body(self):
        self.consume(TokenType.L_PAREN, "Expected opening parenthesis for branch_iter_quantification_body")
        set_whitespace_back_to = self.ignore_whitespace(True)
        quantifier_bodies: list[ast_.IterBody] = [self.iter_quantification_body()]
        self.consume(TokenType.R_PAREN, "Expected closing parenthesis for branch_iter_quantification_body")
        self.ignore_whitespace(set_whitespace_back_to)
        while self.match(TokenType.BACKTICK):
            self.consume(TokenType.L_PAREN, "Expected opening parenthesis for branch_iter_quantification_body")
            set_whitespace_back_to = self.ignore_whitespace(True)
            quantifier_bodies.append(self.iter_quantification_body())
            self.consume(TokenType.R_PAREN, "Expected closing parenthesis for branch_iter_quantification_body")
            self.ignore_whitespace(set_whitespace_back_to)
        return quantifier_bodies

    @store_derivation
    def generator_with_assignments(self):
        generator = self.generator()
        self.consume(TokenType.COLON, "Expected colon after generator in iter_quantification_body")
        initializing_assignments: list[ast_.Assignment] = [self.assignment()]
        while self.match(TokenType.SEMICOLON):
            initializing_assignments.append(self.assignment())
        return ast_.IterGenerator(generator, initializing_assignments)

    @store_derivation
    def iter_block(self):
        if self.peek().type_ != TokenType.NEWLINE:
            simple_stmts = [self.simple_stmt()]
            while self.match(TokenType.SEMICOLON):
                simple_stmts.append(self.simple_stmt())
            return ast_.Statements(simple_stmts)

        self.consume(TokenType.NEWLINE, "Expected newline for block")
        self.consume(TokenType.INDENT, "Expected indentation for block")
        statements = self.statements()
        if self.peek().type_ != TokenType.DEDENT:
            self.consume(TokenType.DEDENT, "Expected dedentation for block")
        self.peek().type_ = TokenType.NEWLINE  # Hack to allow for trailing newline after block
        return statements

    @store_derivation
    def generator(self) -> ast_.Generator:
        bound_identifiers = self.ident_list()
        self.consume(TokenType.IN, "Expected IN token after identifiers in generator")
        expr = self.expr()
        predicate: ast_.ASTNode = ast_.True_()
        if self.match(TokenType.DOT) or self.match(TokenType.CDOT):
            predicate = self.expr()
        return ast_.Generator(bound_identifiers, expr, predicate)

    @store_derivation
    def pair_expr(self) -> ast_.ASTNode:
        return self.left_associative_optional_parse(
            self.rel_set_expr,
            {TokenType.MAPLET: ast_.Maplet},
        )

    @store_derivation
    def rel_set_expr(self) -> ast_.ASTNode:
        set_expr = self.set_expr()
        match self.peek().type_:
            case TokenType.RELATION:
                bin_op: Callable[[ast_.ASTNode, ast_.ASTNode], ast_.RelationOp] = ast_.Relation
            case TokenType.TOTAL_RELATION:
                bin_op = ast_.TotalRelation
            case TokenType.SURJECTIVE_RELATION:
                bin_op = ast_.SurjectiveRelation
            case TokenType.TOTAL_SURJECTIVE_RELATION:
                bin_op = ast_.TotalSurjectiveRelation
            case TokenType.PARTIAL_FUNCTION:
                bin_op = ast_.PartialFunction
            case TokenType.TOTAL_FUNCTION:
                bin_op = ast_.TotalFunction
            case TokenType.PARTIAL_INJECTION:
                bin_op = ast_.PartialInjection
            case TokenType.TOTAL_INJECTION:
                bin_op = ast_.TotalInjection
            case TokenType.PARTIAL_SURJECTION:
                bin_op = ast_.PartialSurjection
            case TokenType.TOTAL_SURJECTION:
                bin_op = ast_.TotalSurjection
            case TokenType.BIJECTION:
                bin_op = ast_.Bijection
            case _:
                return set_expr
        self.advance()
        return bin_op(set_expr, self.rel_set_expr())

    @store_derivation
    def set_expr(self) -> ast_.ASTNode:
        interval_expr = self.interval_expr()
        match bin_token := self.peek().type_:
            case TokenType.UNION:
                bin_op: type[ast_.BinaryOp] = ast_.Union
            case TokenType.CARTESIAN_PRODUCT:
                bin_op = ast_.CartesianProduct
            case TokenType.RELATION_OVERRIDING:
                bin_op = ast_.RelationOverriding
            case TokenType.COMPOSITION:
                bin_op = ast_.Composition
            case TokenType.INTERSECTION:
                bin_op = ast_.Intersection
            case TokenType.CONCAT:
                bin_op = ast_.Concat
            case TokenType.SET_DIFFERENCE:
                bin_op = ast_.Difference
            case TokenType.DOMAIN_SUBTRACTION:
                bin_op = ast_.DomainSubtraction
            case TokenType.DOMAIN_RESTRICTION:
                bin_op = ast_.DomainRestriction
            case TokenType.RANGE_SUBTRACTION:
                bin_op = ast_.RangeSubtraction
            case TokenType.RANGE_RESTRICTION:
                bin_op = ast_.RangeRestriction
            case _:
                return interval_expr

        if bin_token in {
            ast_.BinaryOperator.DOMAIN_SUBTRACTION,
            ast_.BinaryOperator.DOMAIN_RESTRICTION,
            ast_.BinaryOperator.RANGE_SUBTRACTION,
            ast_.BinaryOperator.RANGE_RESTRICTION,
        }:
            self.advance()
            right = self.interval_expr()
            return bin_op(interval_expr, right)  # type: ignore

        n = self.left_associative_optional_parse(
            self.interval_expr,
            {bin_token: bin_op},
            default_left=interval_expr,
        )
        return n

    @store_derivation
    def interval_expr(self) -> ast_.ASTNode:
        arithmetic_expr = self.arithmetic_expr()
        if self.match(TokenType.UPTO):
            arithmetic_expr = ast_.BinaryOp(arithmetic_expr, self.arithmetic_expr(), ast_.BinaryOperator.UPTO)
        return arithmetic_expr

    @store_derivation
    def arithmetic_expr(self) -> ast_.ASTNode:
        return self.left_associative_optional_parse(
            self.term,
            {
                TokenType.PLUS: ast_.Add,
                TokenType.MINUS: ast_.Subtract,
            },
        )

    @store_derivation
    def term(self) -> ast_.ASTNode:
        return self.left_associative_optional_parse(
            self.factor,
            {
                TokenType.MULT: ast_.Multiply,
                TokenType.DIV: ast_.Divide,
                TokenType.MOD: ast_.Modulo,
            },
        )

    @store_derivation
    def factor(self) -> ast_.ASTNode:
        match self.peek().type_:
            case TokenType.PLUS:
                self.advance()
                return self.factor()
            case TokenType.MINUS:
                self.advance()
                return ast_.Negative(self.factor())
            case _:
                return self.power()

    @store_derivation
    def power(self) -> ast_.ASTNode:
        # TODO add alternative, unicode exponents according to the grammar
        primary = self.primary()
        if self.match(TokenType.EXPONENT):
            return ast_.Exponent(primary, self.factor())
        elif self.match(TokenType.INVERSE):
            return ast_.Inverse(primary)
        return primary

    @store_derivation
    def primary(self) -> ast_.ASTNode:
        # TODO match grammar - attempt to parse primary as left recursive?
        atom = self.atom()
        while self.peek().type_ in [TokenType.DOT, TokenType.L_PAREN, TokenType.L_BRACKET]:
            match self.peek().type_:
                case TokenType.DOT:
                    self.advance()
                    t = self.peek()
                    self.consume(TokenType.IDENTIFIER, "Access only allowed through an identifier")
                    atom = ast_.RecordAccess(atom, ast_.Identifier(t.value))
                case TokenType.L_PAREN:
                    set_whitespace_back_to = self.ignore_whitespace(True)
                    self.advance()
                    args = []
                    if self.peek() != TokenType.R_PAREN:
                        args.append(self.expr())
                        while self.match(TokenType.COMMA):
                            args.append(self.expr())
                    self.consume(TokenType.R_PAREN, "Expected closing parenthesis")
                    self.ignore_whitespace(set_whitespace_back_to)
                    atom = ast_.Call(atom, args)
                case TokenType.L_BRACKET:
                    set_whitespace_back_to = self.ignore_whitespace(True)
                    self.advance()
                    args = [self.expr()]
                    while self.match(TokenType.COMMA):
                        args.append(self.expr())
                    self.consume(TokenType.R_BRACKET, "Expected closing bracket")
                    self.ignore_whitespace(set_whitespace_back_to)
                    atom = ast_.Image(atom, args)
                case _:
                    self.error("Unreachable state")
        return atom

    @store_derivation
    def atom(self) -> ast_.ASTNode:
        match (t := self.advance()).type_:
            case TokenType.INTEGER:
                return ast_.Int(t.value)
            case TokenType.FLOAT:
                return ast_.Float(t.value)
            case TokenType.STRING:
                return ast_.String(t.value)
            case TokenType.TRUE:
                return ast_.True_()
            case TokenType.FALSE:
                return ast_.False_()
            case TokenType.L_BRACE:
                set_whitespace_back_to = self.ignore_whitespace(True)
                set_ = self.set_()
                self.ignore_whitespace(set_whitespace_back_to)
                return set_
            case TokenType.L_BRACKET:
                set_whitespace_back_to = self.ignore_whitespace(True)
                sequence = self.sequence()
                self.ignore_whitespace(set_whitespace_back_to)
                return sequence
            case TokenType.L_DOUBLE_BRACKET:
                set_whitespace_back_to = self.ignore_whitespace(True)
                bag = self.bag()
                self.ignore_whitespace(set_whitespace_back_to)
                return bag
            case TokenType.L_PAREN:
                set_whitespace_back_to = self.ignore_whitespace(True)
                if self.peek().type_ == TokenType.R_PAREN:
                    self.advance()
                    self.ignore_whitespace(set_whitespace_back_to)
                    return ast_.TupleLiteral([])

                expr = self.expr()

                if self.peek().type_ != TokenType.COMMA:
                    self.consume(TokenType.R_PAREN, "Need to close parenthesis")
                    self.ignore_whitespace(set_whitespace_back_to)
                    return expr

                exprs = [expr]
                while self.match(TokenType.COMMA):
                    exprs.append(self.expr())
                self.consume(TokenType.R_PAREN, "Need to close tuple literal")
                self.ignore_whitespace(set_whitespace_back_to)
                return ast_.TupleLiteral(exprs)

            case TokenType.IDENTIFIER:
                return ast_.Identifier(t.value)
            # FIXME The below tokens should be reserved for quantification. What should we do about the function versions?
            case x if x in TOKENS_THAT_CAN_ACT_AS_FUNC_IDENTIFIERS:
                return ast_.Identifier(TOKENS_THAT_CAN_ACT_AS_FUNC_IDENTIFIERS[x])
            case _:
                self.error("Failed to interpret first token of expected atom")

    @store_derivation
    def collection_body(self, collection_operator: ast_.CollectionOperator, closing_symbol: TokenType) -> ast_.ASTNode:
        if self.match(TokenType.NEWLINE):
            self.match(TokenType.INDENT)

        # Since sets may start with an ident_list even if they are just set enumeration,
        # we need to use similar hacks to quantification body
        starting_index = self.current_index

        # Handle empty set
        if self.match(closing_symbol):
            return ast_.Enumeration([], collection_operator)

        # Then try set enumeration with one elem
        # FIXME This comma trick wont work because actual generators can use commas now
        try:
            enumeration = [self.expr()]
            while self.match(TokenType.COMMA):
                if self.match(TokenType.NEWLINE):
                    self.match(TokenType.INDENT)
                enumeration.append(self.expr())

            if self.match(TokenType.NEWLINE):
                self.match(TokenType.DEDENT)

            if self.match(closing_symbol):
                return ast_.Enumeration(enumeration, collection_operator)
        except ParseException:
            logger.debug(f"Failed to parse as enumeration, trying as quantification. Parse error was: {self.errors[-1]}")
            self.errors.pop()  # remove the parseException cause by attempting to match on expr directly

        # backtrack - this is not an enumeration, rather a quantification
        self.current_index = starting_index
        body = self.quantification_body()

        quantification_operator = ast_.QuantifierOperator.from_collection_operator(collection_operator)
        if quantification_operator is None:
            self.error(f"Failed to convert collection operator {collection_operator} to quantification operator")
        self.consume(closing_symbol, f"Expected closing symbol for collection")
        return ast_.Quantifier3(body, quantification_operator)

    @store_derivation
    def set_(self) -> ast_.ASTNode:
        collection = self.collection_body(ast_.CollectionOperator.SET, TokenType.R_BRACE)
        # Awkwardly, we separate relations from sets post tree creation
        if isinstance(collection, ast_.Enumeration):
            if not collection.items:
                # Empty set, return empty set enumeration
                return collection

            # Test all enum elements for maplets. If even one is not of maplet form, keep everything as a set
            for elem in collection.items:
                if not isinstance(elem, ast_.BinaryOp):
                    return collection
                if elem.op_type != ast_.BinaryOperator.MAPLET:
                    # If the element is not a maplet, we cannot promote the whole set to a relation
                    return collection
            # otherwise, promote it to a relation
            return ast_.RelationEnumeration(collection.items)  # type: ignore

        # TODO handle relations post-symbol table?
        # if isinstance(collection, ast_.Quantifier2):
        #     # Maplet should always be top level in the expression.
        #     # FIXME but this is not 100% reliable since an identifier or other expr could produce a maplet
        #     if not isinstance(collection.expression, ast_.BinaryOp):
        #         return collection
        #     if collection.expression.op_type != ast_.BinaryOperator.MAPLET:
        #         # If the expression is not a maplet, we cannot promote the whole set to a relation
        #         return collection

        #     collection.op_type = ast_.QuantifierOperator.RELATION
        return collection

    @store_derivation
    def bag(self) -> ast_.ASTNode:
        return self.collection_body(ast_.CollectionOperator.BAG, TokenType.R_DOUBLE_BRACKET)

    @store_derivation
    def sequence(self) -> ast_.ASTNode:
        return self.collection_body(ast_.CollectionOperator.SEQUENCE, TokenType.R_BRACKET)

    @store_derivation
    def control_flow_stmt(self) -> ast_.ASTNode:
        match self.advance().type_:
            case TokenType.RETURN:
                # This may try to eat up the next line? might need a statement separator...
                if self.peek().type_ not in self.get_first_set("expr"):
                    return ast_.Return(ast_.None_())
                return ast_.Return(self.expr())
            case TokenType.BREAK:
                return ast_.Break()
            case TokenType.CONTINUE:
                return ast_.Continue()
            case TokenType.SKIP:
                return ast_.Skip()
            case _:
                self.error("Invalid start to control flow statement")

    @store_derivation
    def import_stmt(self) -> ast_.ASTNode:
        t = self.advance()
        import_name = self.advance()
        if import_name.type_ != TokenType.STRING:
            self.error("Expected import name to be a string literal (file path)")

        module_file_path = Path(import_name.value)
        if not self.source_file_path:
            self.error("Importing is not supported for simile contents without a base file path")
        if not module_file_path.is_absolute():
            module_file_path = self.source_file_path.parent / import_name.value

        match t.type_:
            case TokenType.FROM:
                self.consume(TokenType.IMPORT, "Expected 'import' after 'from'")
                import_objects, import_operator = self.import_list()
                return ast_.Import(module_file_path, import_objects, import_operator)
            case TokenType.IMPORT:
                return ast_.Import(module_file_path, [], ast_.ImportOperator.MODULE_NAME)
            case _:
                self.error(f"Unexpected token {t}")

    @store_derivation
    def import_list(self) -> tuple[list[str], ast_.ImportOperator]:
        if self.match(TokenType.MULT):
            return [], ast_.ImportOperator.ALL_NAMES
        # use flat_tuple_identifier for the parsing benefits (ex. for multi-line tuples)
        # but then just extract the str result from the flattened list
        named_identifiers = self.flat_tuple_identifier()
        plain_names: list[str] = []
        for ident in named_identifiers.items:
            if not isinstance(ident, ast_.Identifier):
                self.error(f"Expected identifier in import list (parsed up to {plain_names})")
            plain_names.append(ident.name)
        return plain_names, ast_.ImportOperator.SPECIFIC_NAMES

    @store_derivation
    def flat_tuple_identifier(self) -> ast_.TupleIdentifier:
        matched_paren = self.match(TokenType.L_PAREN)
        set_whitespace_back_to = self.ignore_whitespace_
        if matched_paren:
            set_whitespace_back_to = self.ignore_whitespace(True)

        t = self.peek()
        self.consume(TokenType.IDENTIFIER, "Expected identifier tuple identifier")
        items = [ast_.Identifier(t.value)]

        while self.match(TokenType.COMMA):
            t = self.advance()
            if t.type_ != TokenType.IDENTIFIER:
                self.error(f"Expected identifier in tuple identifier (parsed up to {items})")
            items.append(ast_.Identifier(t.value))

        if matched_paren:
            self.consume(TokenType.R_PAREN, "Expected closing parenthesis for tuple identifier")
            self.ignore_whitespace(set_whitespace_back_to)
        return ast_.TupleIdentifier(tuple(items))

    @store_derivation
    def compound_stmt(self) -> ast_.ASTNode:
        match self.advance().type_:
            case TokenType.IF:
                return self.if_stmt()
            case TokenType.FOR:
                return self.for_stmt()
            case TokenType.WHILE:
                return self.while_stmt()
            case TokenType.RECORD:
                return self.record_stmt()
            # case TokenType.ENUM:
            #     return self.enum_stmt()
            case TokenType.PROCEDURE:
                return self.procedure_stmt()
            case _:
                self.error("Invalid start to compound statement")

    @store_derivation
    def if_stmt(self) -> ast_.If:
        condition = self.predicate()
        self.consume(TokenType.COLON, "Expected colon after IF condition")
        block = self.block()
        if self.match(TokenType.ELSE):
            if self.match(TokenType.IF):
                return ast_.If(condition, block, self.elif_stmt())
            else:
                return ast_.If(condition, block, self.else_stmt())
        else:
            return ast_.If(condition, block, ast_.None_())

    @store_derivation
    def elif_stmt(self) -> ast_.ElseIf:
        condition = self.predicate()
        self.consume(TokenType.COLON, "Expected colon after ELIF condition")
        block = self.block()
        if self.match(TokenType.ELSE):
            if self.match(TokenType.IF):
                return ast_.ElseIf(condition, block, self.elif_stmt())
            else:
                return ast_.ElseIf(condition, block, self.else_stmt())
        else:
            return ast_.ElseIf(condition, block, ast_.None_())

    @store_derivation
    def else_stmt(self) -> ast_.Else:
        self.consume(TokenType.COLON, "Expected colon after ELSE")
        block = self.block()
        return ast_.Else(block)

    @store_derivation
    def for_stmt(self) -> ast_.For:
        ident_list = self.ident_list()
        self.consume(TokenType.IN, "Expected 'in' after identifier list in FOR statement")
        iterable = self.expr()
        self.consume(TokenType.COLON, "Expected colon after iterable in FOR statement")
        block = self.block()
        return ast_.For(ident_list, iterable, block)

    @store_derivation
    def while_stmt(self) -> ast_.While:
        condition = self.predicate()
        self.consume(TokenType.COLON, "Expected colon after WHILE condition")
        block = self.block()
        return ast_.While(condition, block)

    @store_derivation
    def record_stmt(self) -> ast_.RecordDefIdentifier:
        t = self.advance()
        if t.type_ != TokenType.IDENTIFIER:
            self.error("Expected identifier after RECORD keyword")
        name = ast_.Identifier(t.value)

        self.consume(TokenType.COLON, "Expected colon after RECORD name")
        self.consume(TokenType.NEWLINE, "Expected newline after RECORD definition")
        self.consume(TokenType.INDENT, "Expected indentation after RECORD definition")
        if self.match(TokenType.SKIP):
            items = []
            self.consume(TokenType.NEWLINE, "Expected newline after PASS in RECORD definition")
        else:
            items = [self.typed_name()]
            while self.peek().type_ == TokenType.COMMA or self.peek().type_ == TokenType.NEWLINE:
                if self.peek(1).type_ == TokenType.DEDENT:
                    self.consume(TokenType.NEWLINE, "Expected newline after last RECORD item")
                    break
                if self.match(TokenType.COMMA):
                    self.match(TokenType.NEWLINE)
                else:
                    self.consume(TokenType.NEWLINE, "Expected newline or comma after RECORD item")
                items.append(self.typed_name())
        self.consume(TokenType.DEDENT, "Expected dedent after RECORD definition")
        return ast_.RecordDefIdentifier(name, items)

    @store_derivation
    def procedure_stmt(self) -> ast_.ProcedureDefIdentifier:
        t = self.advance()
        if t.type_ != TokenType.IDENTIFIER:
            self.error("Expected identifier after DEF keyword")
        name = ast_.Identifier(t.value)

        self.consume(TokenType.L_PAREN, "Expected opening parenthesis for procedure parameters")
        set_whitespace_back_to = self.ignore_whitespace(True)
        params = []
        if self.peek().type_ != TokenType.R_PAREN:
            params.append(self.typed_name())
            while self.match(TokenType.COMMA):
                params.append(self.typed_name())
        self.consume(TokenType.R_PAREN, "Expected closing parenthesis for procedure parameters")
        self.ignore_whitespace(set_whitespace_back_to)

        self.consume(TokenType.RIGHTARROW, "Expected right arrow after procedure parameters")
        return_type = self.type_expr()
        self.consume(TokenType.COLON, "Expected colon after procedure type")
        block = self.block()
        return ast_.ProcedureDefIdentifier(name, params, block, return_type)

    @store_derivation
    def typed_name(self) -> ast_.TypedName:
        t = self.advance()
        if t.type_ != TokenType.IDENTIFIER:
            self.error("Expected identifier for typed name")
        name = ast_.Identifier(t.value)

        if self.match(TokenType.COLON):
            type_annotation = self.type_expr()
            return ast_.TypedName(name, type_annotation)
        return ast_.TypedName(name, ast_.None_())

    @store_derivation
    def block(self) -> ast_.Statements:
        if self.peek().type_ != TokenType.NEWLINE:
            return ast_.Statements([self.simple_statements()])

        self.consume(TokenType.NEWLINE, "Expected newline for block")
        self.consume(TokenType.INDENT, "Expected indentation for block")
        statements = self.statements()
        self.consume(TokenType.DEDENT, "Expected dedentation for block")
        return statements


def parse(source_text: str, source_file_path: Path | None = None) -> ast_.Start:
    """Parse a list of tokens into an abstract syntax tree (AST)."""
    tokens = scan(source_text)
    tokens_without_comments = list(filter(lambda t: t.type_ != TokenType.COMMENT, tokens))
    parser = Parser(tokens_without_comments, source_text, source_file_path)
    res = parser.start()

    if not parser.errors:
        return res

    raise ParseError(parser)
