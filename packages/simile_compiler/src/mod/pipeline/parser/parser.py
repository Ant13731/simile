from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Any, NoReturn, TypeVar, Mapping
import inspect
from functools import wraps

from colorama import just_fix_windows_console
from termcolor import colored


from src.mod.pipeline.scanner import Token, TokenType, scan
from src.mod.data import ast_

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")
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
    original_text: str = ""  # Used only for error messages
    current_index: int = 0
    errors: list[ParseErr] = field(default_factory=list)
    derivation: list[str] = field(default_factory=list)

    # Idea: store the first sets and the corresponding functions (that would otherwise be "matched" when making decisions)
    # It may be nice to allow for nested first sets and then a lookup (using the idea of getting all leaves from a tree...)

    # Idea 2: store a mapping of production names -> first sets. first sets may include references to other productions
    # (ie. using strings instead of TokenTypes)
    first_sets: ClassVar[dict[str, set[str | TokenType]]] = {
        "start": {TokenType.EOF, "statements"},
        "statements": {TokenType.COMMENT, "simple_stmt", "compound_stmt"},
        "simple_stmt": {"expr", "assignment", "control_flow_stmt", "import_stmt"},
        "predicate": {"bool_quantification", "unquantified_predicate"},
        "bool_quantification": {TokenType.FORALL, TokenType.EXISTS},
        "ident_list": {"ident_pattern"},
        "ident_pattern": {TokenType.IDENTIFIER, TokenType.L_PAREN},
        "unquantified_predicate": {"implication"},
        "implication": {"impl", "rev_impl", "disjunction"},
        "impl": {"disjunction"},
        "rev_impl": {"disjunction"},
        "disjunction": {"conjunction"},
        "conjunction": {"negation"},
        "negation": {TokenType.NOT, "atom_bool"},
        "atom_bool": {TokenType.TRUE, TokenType.FALSE, TokenType.L_PAREN, "pair_expr"},
        "expr": {"quantification", "pair_expr", "predicate"},
        "quantification": {"lambdadef", "quantification_op"},
        "quantification_op": {TokenType.GENERAL_UNION, TokenType.GENERAL_INTERSECTION},
        "quantification_body": {"ident_list", "expr"},
        "lambdadef": {TokenType.LAMBDA},
        "pair_expr": {"rel_set_expr"},
        "rel_set_expr": {"set_expr"},
        "set_expr": {"interval_expr", "rel_expr"},
        "rel_expr": {"interval_expr"},
        "rel_sub_expr": {"range_modifier", TokenType.SET_DIFFERENCE},
        "range_modifier": {TokenType.RANGE_RESTRICTION, TokenType.RANGE_SUBTRACTION},
        "interval_expr": {"arithmetic_expr"},
        "arithmetic_expr": {"term"},
        "term": {"factor"},
        "factor": {TokenType.PLUS, TokenType.MINUS, "power"},
        "power": {"primary"},
        "primary": {"struct_access", "call", "image"},
        # "inversable_atom": {"atom"},
        "struct_access": {"atom"},
        "call": {"atom"},
        "image": {"atom"},
        "atom": {
            TokenType.IDENTIFIER,
            TokenType.L_PAREN,
            TokenType.INTEGER,
            TokenType.FLOAT,
            TokenType.STRING,
            TokenType.TRUE,
            TokenType.FALSE,
            TokenType.NONE,
            "collections",
            "builtin_functions",
        },
        "collections": {"set", "sequence", "bag"},  # handle relation inside the parsing function
        "set": {TokenType.L_BRACE},
        "sequence": {TokenType.L_BRACKET},
        "bag": {TokenType.L_DOUBLE_BRACKET},
        "builtin_functions": {TokenType.POWERSET, TokenType.NONEMPTY_POWERSET},  # , TokenType.CARDINALITY, TokenType.FIRST, TokenType.SECOND},
        "control_flow_stmt": {TokenType.RETURN, TokenType.BREAK, TokenType.CONTINUE, TokenType.SKIP},
        "assignment": {"struct_access"},
        "typed_name": {TokenType.IDENTIFIER},
        "compound_stmt": {
            "if_stmt",
            "for_stmt",
            "while_stmt",
            "record_stmt",
            # "enum_stmt",
            "procedure_stmt",
        },
        "if_stmt": {TokenType.IF},
        "else_stmt": {TokenType.ELSE},
        "for_stmt": {TokenType.FOR},
        "while_stmt": {TokenType.WHILE},
        "record_stmt": {TokenType.RECORD},
        # "enum_stmt": {TokenType.ENUM},
        "procedure_stmt": {TokenType.PROCEDURE},
        "block": {"simple_stmt", TokenType.INDENT},
        "import_stmt": {TokenType.IMPORT, TokenType.FROM},
        "import_name": {TokenType.DOT, TokenType.IDENTIFIER},
        "import_list": {TokenType.MULT, TokenType.IDENTIFIER, TokenType.L_PAREN},
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

    def peek(self, offset: int = 0) -> Token:
        return self.tokens[self.current_index + offset]

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

                if self.peek().type_ in self.get_first_set("simple_stmt"):
                    statements.append(self.simple_stmt())
                elif self.peek().type_ in self.get_first_set("compound_stmt"):
                    statements.append(self.compound_stmt())
                else:
                    self.error("Unexpected statement starter")
            except ParseException:
                self.synchronize()

        return ast_.Statements(statements)

    @store_derivation
    def simple_stmt(self) -> ast_.SimpleStmt | ast_.ASTNode:
        t = self.peek()
        if t.type_ in self.get_first_set("expr"):
            expr = self.expr()
            if self.peek().type_ not in [TokenType.COLON, TokenType.ASSIGN, TokenType.CHOICE_ASSIGN]:
                self.consume(TokenType.NEWLINE, "Expected end of simple statement or assignment after parsing expression")
                return expr

            # now in assignment rule - could either see a type annotation or not
            if self.match(TokenType.COLON):
                type_ = self.expr()

                def replace_image_with_generic_type_(node: ast_.ASTNode | Any) -> ast_.ASTNode | None:
                    match node:
                        case ast_.Image(ast_.Identifier(_) as target, index):
                            return ast_.Type_(target, [index])
                    return None

                rewritten_type_ = ast_.Type_(type_.find_and_replace_with_func(replace_image_with_generic_type_))
                expr = ast_.TypedName(expr, rewritten_type_)

            if self.match(TokenType.CHOICE_ASSIGN):
                choice_assignment = True
            else:
                choice_assignment = False
                self.consume(TokenType.ASSIGN, "Expected assignment after an expression not ending with a newline")

            # Since first of assignment and expr are shared, check if next token is an assignment
            value = self.expr()
            self.consume(TokenType.NEWLINE, "Expected end of simple statement after assignment")

            # handle type restrictions, datatype refinements, etc.
            with_clauses = []
            if self.peek().type_ == TokenType.INDENT:
                self.advance()
                while not self.match(TokenType.DEDENT):
                    self.consume(TokenType.WITH, "Each refinement line in an assignment block must start with 'with'")
                    with_clauses.append(self.expr())
                    self.consume(TokenType.NEWLINE, "Expected newline after with clause expression")

            return ast_.Assignment(target=expr, value=value, with_clauses=with_clauses, choice_assignment=choice_assignment)
        if t.type_ in self.get_first_set("control_flow_stmt"):
            stmt = self.control_flow_stmt()
            self.consume(TokenType.NEWLINE, "Expected end of simple statement after control flow statement")
            return stmt
        if t.type_ in self.get_first_set("import_stmt"):
            stmt = self.import_stmt()
            self.consume(TokenType.NEWLINE, "Expected end of simple statement after import statement")
            return stmt
        self.error("Invalid start to simple_stmt")

    @store_derivation
    def predicate(self) -> ast_.Predicate | ast_.ASTNode:
        t = self.peek()
        match t.type_:
            case TokenType.FORALL:
                self.advance()
                ident_list = self.ident_list()
                if not self.match(TokenType.DOT):
                    self.consume(TokenType.CDOT, "Expected FORALL quantification separator")
                predicate = self.predicate()
                if not isinstance(predicate, ast_.ListOp):
                    predicate = ast_.And([predicate])

                forall = ast_.Forall(predicate)
                forall._bound_identifiers = set(ident_list.flatten_until_leaf_node())
                return forall
            case TokenType.EXISTS:
                self.advance()
                ident_list = self.ident_list()
                if not self.match(TokenType.DOT):
                    self.consume(TokenType.CDOT, "Expected EXISTS quantification separator")
                predicate = self.predicate()
                if not isinstance(predicate, ast_.ListOp):
                    predicate = ast_.And([predicate])

                exists = ast_.Exists(predicate)
                exists._bound_identifiers = set(ident_list.flatten_until_leaf_node())
                return exists
            case _ if t.type_ in self.get_first_set("unquantified_predicate"):
                return self.unquantified_predicate()
            case _:
                self.error("Predicate token not found")

    @store_derivation
    def ident_list(self) -> ast_.TupleIdentifier:
        ident_list_items = [self.ident_list_item()]
        while self.match(TokenType.COMMA):
            ident_list_items.append(self.ident_list_item())
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
                self.advance()
                item = self.ident_list()
                self.consume(TokenType.R_PAREN, "Expected end to identifier item sub-list")
            case _:
                self.error("No identifier or sub-pattern found")
        return item

    @store_derivation
    def unquantified_predicate(self) -> ast_.ASTNode:
        return self.left_associative_optional_parse(
            self.implication,
            {
                TokenType.EQUIVALENT: ast_.Equivalent,
                TokenType.NOT_EQUIVALENT: ast_.NotEquivalent,
            },
        )

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
        # if self.match(TokenType.TRUE):
        #     return ast_.True_()
        # if self.match(TokenType.FALSE):
        #     return ast_.False_()
        # if self.match(TokenType.L_PAREN):
        #     predicate = self.predicate()
        #     self.consume(TokenType.R_PAREN, "Missing closing parenthesis")
        #     return predicate
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
            case TokenType.GENERAL_UNION:
                ident_list, predicate, expression = self.quantification_body()
                union_all: ast_.ASTNode = ast_.UnionAll(predicate, expression)
                if ident_list:
                    union_all = ast_.QualifiedUnionAll(ident_list, predicate, expression)
                # union_all._bound_identifiers = set(ident_list.flatten_until_leaf_node())
                return union_all
            case TokenType.GENERAL_INTERSECTION:
                ident_list, predicate, expression = self.quantification_body()
                intersection_all: ast_.ASTNode = ast_.IntersectionAll(predicate, expression)
                if ident_list:
                    intersection_all = ast_.QualifiedIntersectionAll(ident_list, predicate, expression)
                # intersection_all._bound_identifiers = set(ident_list.flatten_until_leaf_node())
                return intersection_all
            case _:
                self.error("Invalid start to quantification")

    @store_derivation
    def quantification_body(self) -> tuple[ast_.TupleIdentifier | None, ast_.ListOp, ast_.ASTNode]:
        # expr should cover the first entry in a list of identifiers,
        starting_index = self.current_index
        first_part = self.expr()
        # but in the case that we see a comma or single identifier list (via cdot),
        # backtrack and reparse as an identifier
        if self.peek().type_ in [TokenType.COMMA, TokenType.CDOT, TokenType.DOT]:
            self.current_index = starting_index
            first_part = self.ident_list()

        if self.match(TokenType.DOT) or self.match(TokenType.CDOT):
            predicate = self.predicate()
            if not isinstance(predicate, ast_.ListOp):
                predicate = ast_.And([predicate])

            self.consume(TokenType.VBAR, "Expected quantification predicate separator")
            expression = self.expr()
            if not isinstance(first_part, ast_.TupleIdentifier):
                self.error("Failed to parse quantification body - the identifier list in long form is not of type IdentList")
            return first_part, predicate, expression

        self.consume(TokenType.VBAR, "Expected quantification predicate separator (shorthand)")
        predicate = self.predicate()
        if not isinstance(predicate, ast_.ListOp):
            predicate = ast_.And([predicate])
        return None, predicate, first_part

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
        match self.peek().type_:
            case TokenType.UNION:
                bin_op: type[ast_.BinaryOp] = ast_.Union
                bin_token: TokenType = TokenType.UNION
            case TokenType.CARTESIAN_PRODUCT:
                bin_op = ast_.CartesianProduct
                bin_token = TokenType.CARTESIAN_PRODUCT
            case TokenType.RELATION_OVERRIDING:
                bin_op = ast_.RelationOverriding
                bin_token = TokenType.RELATION_OVERRIDING
            case TokenType.COMPOSITION:
                bin_op = ast_.Composition
                bin_token = TokenType.COMPOSITION
            case TokenType.INTERSECTION:
                bin_op = ast_.Intersection
                bin_token = TokenType.INTERSECTION
            case TokenType.CONCAT:
                bin_op = ast_.Concat
                bin_token = TokenType.CONCAT
            case TokenType.DOMAIN_SUBTRACTION:
                self.advance()
                right = self.left_associative_optional_parse(
                    self.interval_expr,
                    {TokenType.INTERSECTION: ast_.Intersection},
                )
                if self.peek().type_ in self.get_first_set("rel_sub_expr"):
                    right = self.rel_sub_expr()(right)
                return ast_.BinaryOp(interval_expr, right, ast_.BinaryOperator.DOMAIN_SUBTRACTION)
            case TokenType.DOMAIN_RESTRICTION:
                self.advance()
                right = self.left_associative_optional_parse(
                    self.interval_expr,
                    {TokenType.INTERSECTION: ast_.Intersection},
                )
                if self.peek().type_ in self.get_first_set("rel_sub_expr"):
                    right = self.rel_sub_expr()(right)
                return ast_.BinaryOp(interval_expr, right, ast_.BinaryOperator.DOMAIN_RESTRICTION)
            case x if x in self.get_first_set("rel_sub_expr"):
                return self.rel_sub_expr()(interval_expr)
            case _:
                return interval_expr

        # self.advance()
        n = self.left_associative_optional_parse(
            self.interval_expr,
            {bin_token: bin_op},
            default_left=interval_expr,
        )

        if bin_token == TokenType.INTERSECTION:
            if self.peek().type_ in self.get_first_set("rel_sub_expr"):
                n = self.rel_sub_expr()(n)
        return n

    @store_derivation
    def rel_sub_expr(self) -> Callable[[ast_.ASTNode], ast_.ASTNode]:
        match self.advance().type_:
            case TokenType.SET_DIFFERENCE:
                return lambda n: ast_.BinaryOp(n, self.interval_expr(), ast_.BinaryOperator.DIFFERENCE)
            case TokenType.RANGE_RESTRICTION:
                return lambda n: ast_.BinaryOp(n, self.interval_expr(), ast_.BinaryOperator.RANGE_RESTRICTION)
            case TokenType.RANGE_SUBTRACTION:
                return lambda n: ast_.BinaryOp(n, self.interval_expr(), ast_.BinaryOperator.RANGE_SUBTRACTION)
            case t:
                self.error(f"Unexpected token {t}")

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
        atom = self.atom()
        while self.peek().type_ in [TokenType.DOT, TokenType.L_PAREN, TokenType.L_BRACKET]:
            match self.peek().type_:
                case TokenType.DOT:
                    self.advance()
                    t = self.peek()
                    self.consume(TokenType.IDENTIFIER, "Access only allowed through an identifier")
                    atom = ast_.StructAccess(atom, ast_.Identifier(t.value))
                case TokenType.L_PAREN:
                    self.advance()
                    args = []
                    if self.peek() != TokenType.R_PAREN:
                        args.append(self.expr())
                        while self.match(TokenType.COMMA):
                            args.append(self.expr())
                    self.consume(TokenType.R_PAREN, "Expected closing parenthesis")
                    atom = ast_.Call(atom, args)
                case TokenType.L_BRACKET:
                    self.advance()
                    expr = self.expr()
                    self.consume(TokenType.R_BRACKET, "Expected closing bracket")
                    atom = ast_.Image(atom, expr)
                case _:
                    self.error("Unreachable state")
        return atom

    # @store_derivation
    # def inversable_atom(self) -> ast_.ASTNode:
    #     atom = self.atom()
    #     while self.match(TokenType.INVERSE):
    #         atom = ast_.Inverse(atom)
    #     return atom

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
            # case TokenType.NONE:
            #     return ast_.None_()
            case TokenType.L_BRACE:
                return self.set_()
            case TokenType.L_BRACKET:
                return self.sequence()
            case TokenType.L_DOUBLE_BRACKET:
                return self.bag()
            case TokenType.POWERSET:
                self.consume(TokenType.L_PAREN, "Powerset requires object call notation")
                powerset = self.expr()
                self.consume(TokenType.R_PAREN, "Need to close parenthesis")
                return ast_.Powerset(powerset)
            case TokenType.NONEMPTY_POWERSET:
                self.consume(TokenType.L_PAREN, "Nonempty Powerset requires object call notation")
                powerset = self.expr()
                self.consume(TokenType.R_PAREN, "Need to close parenthesis")
                return ast_.NonemptyPowerset(powerset)
            # case TokenType.CARDINALITY:
            #     self.consume(TokenType.L_PAREN, "Cardinality requires object call notation")
            #     cardinality = self.expr()
            #     self.consume(TokenType.R_PAREN, "Need to close parenthesis")
            #     fresh_variable = ast_.Identifier(f"*fresh_var_card{self.current_index}")
            #     # Inlined rewrite rule - Cardinality
            #     ast_sum = ast_.Sum(
            #         ast_.And([ast_.In(fresh_variable, cardinality)]),
            #         ast_.Int("1"),
            #     )
            #     ast_sum._bound_identifiers = {fresh_variable}
            #     return ast_sum
            # case TokenType.FIRST:
            #     self.consume(TokenType.L_PAREN, "First requires object call notation")
            #     first = self.expr()
            #     self.consume(TokenType.R_PAREN, "Need to close parenthesis")
            #     return ast_.Call(ast_.Identifier("*first"), [first])
            # case TokenType.SECOND:
            #     self.consume(TokenType.L_PAREN, "Second requires object call notation")
            #     second = self.expr()
            #     self.consume(TokenType.R_PAREN, "Need to close parenthesis")
            #     return ast_.Call(ast_.Identifier("*second"), [second])
            case TokenType.L_PAREN:
                expr = self.expr()
                self.consume(TokenType.R_PAREN, "Need to close parenthesis")
                return expr
            case TokenType.IDENTIFIER:
                return ast_.Identifier(t.value)
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
        enumeration = [self.expr()]
        while self.match(TokenType.COMMA):
            if self.match(TokenType.NEWLINE):
                self.match(TokenType.INDENT)
            enumeration.append(self.expr())

        if self.match(TokenType.NEWLINE):
            self.match(TokenType.DEDENT)

        if self.match(closing_symbol):
            return ast_.Enumeration(enumeration, collection_operator)

        # backtrack - this is not an enumeration, rather a quantification
        self.current_index = starting_index
        ident_list, predicate, expression = self.quantification_body()
        quantification_operator = ast_.QuantifierOperator.from_collection_operator(collection_operator)
        if quantification_operator is None:
            self.error(f"Failed to convert collection operator {collection_operator} to quantification operator")

        ret: ast_.ASTNode = ast_.Quantifier(predicate, expression, quantification_operator)
        if ident_list:
            ret = ast_.QualifiedQuantifier(ident_list, predicate, expression, quantification_operator)
        # ret._bound_identifiers = set(ident_list.flatten_until_leaf_node()) # TODO remove
        self.consume(closing_symbol, f"Expected closing symbol for collection")
        return ret

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

        if isinstance(collection, ast_.Quantifier):
            # Test only the identifiers for maplets. If no identifiers, test the (single) expression
            # for identifier in collection.bound_identifiers.items:
            #     if not isinstance(identifier, ast_.Maplet):
            #         return collection

            # # List is empty => shorthand version using the expression
            # if not collection.bound_identifiers.items:
            #     if not isinstance(collection.expression, ast_.Maplet):
            #         return collection

            # Maplet should always be top level in the expression
            if not isinstance(collection.expression, ast_.BinaryOp):
                return collection
            if collection.expression.op_type != ast_.BinaryOperator.MAPLET:
                # If the expression is not a maplet, we cannot promote the whole set to a relation
                return collection

            # Otherwise, promote
            ret = ast_.RelationComprehension(
                collection.predicate,
                collection.expression,
            )
            ret._bound_identifiers = collection._bound_identifiers
            return ret
        self.error("Unreachable state in set derivation. The type of the parsed value should be either a SetEnumeration or SetComprehension")

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
        # import_name = self.import_name()
        if t.type_ == TokenType.FROM:
            self.consume(TokenType.IMPORT, "Expected 'import' after 'from'")
            import_objects = self.import_list()
            return ast_.Import(import_name.value, import_objects)
        elif t.type_ == TokenType.IMPORT:
            return ast_.Import(import_name.value, ast_.None_())
        else:
            self.error(f"Unexpected token {t}")

    # @store_derivation
    # def import_name(self) -> list[ast_.Identifier]:
    #     import_path = []
    #     if self.match(TokenType.DOT):
    #         import_path.append(ast_.Identifier("."))

    #     t = self.advance()
    #     if t.type_ == TokenType.IDENTIFIER:
    #         import_path.append(ast_.Identifier(t.value))
    #     else:
    #         self.error("Expected identifier after import dot")

    #     while self.match(TokenType.DOT):
    #         t = self.advance()
    #         if t.type_ == TokenType.IDENTIFIER:
    #             import_path.append(ast_.Identifier(t.value))
    #         else:
    #             self.error(f"Expected identifier after import dot (parsed up to {import_path})")

    #     return import_path

    @store_derivation
    def import_list(self) -> ast_.TupleIdentifier | ast_.ImportAll:
        if self.match(TokenType.MULT):
            return ast_.ImportAll()
        return self.flat_tuple_identifier()

    @store_derivation
    def flat_tuple_identifier(self) -> ast_.TupleIdentifier:
        matched_paren = self.match(TokenType.L_PAREN)

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
    def record_stmt(self) -> ast_.RecordDef:
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
        return ast_.RecordDef(name, items)

    # @store_derivation
    # def enum_stmt(self) -> ast_.EnumDef:
    #     t = self.advance()
    #     if t.type_ != TokenType.IDENTIFIER:
    #         self.error("Expected identifier after ENUM keyword")
    #     name = ast_.Identifier(t.value)

    #     self.consume(TokenType.COLON, "Expected colon after ENUM name")
    #     self.consume(TokenType.NEWLINE, "Expected newline after ENUM definition")
    #     self.consume(TokenType.INDENT, "Expected indentation after ENUM definition")
    #     if self.match(TokenType.PASS):
    #         self.advance()
    #         items = []
    #     else:
    #         t = self.advance()
    #         if t.type_ != TokenType.IDENTIFIER:
    #             self.error("Expected identifier after ENUM keyword")
    #         items = [ast_.Identifier(t.value)]
    #         while self.peek().type_ == TokenType.COMMA or self.peek().type_ == TokenType.NEWLINE:
    #             if self.peek(1).type_ == TokenType.DEDENT:
    #                 self.consume(TokenType.NEWLINE, "Expected newline after last ENUM item")
    #                 break
    #             if self.match(TokenType.COMMA):
    #                 self.match(TokenType.NEWLINE)
    #             else:
    #                 self.consume(TokenType.NEWLINE, "Expected newline or comma after ENUM item")

    #             t = self.peek()
    #             self.consume(TokenType.IDENTIFIER, "Expected identifier after ENUM separator (comma/newline)")
    #             items.append(ast_.Identifier(t.value))

    #     self.consume(TokenType.DEDENT, "Expected dedent after ENUM definition")
    #     return ast_.EnumDef(name, items)

    @store_derivation
    def procedure_stmt(self) -> ast_.ProcedureDef:
        t = self.advance()
        if t.type_ != TokenType.IDENTIFIER:
            self.error("Expected identifier after DEF keyword")
        name = ast_.Identifier(t.value)

        self.consume(TokenType.L_PAREN, "Expected opening parenthesis for procedure parameters")
        params = []
        if self.peek().type_ != TokenType.R_PAREN:
            params.append(self.typed_name())
            while self.match(TokenType.COMMA):
                params.append(self.typed_name())
        self.consume(TokenType.R_PAREN, "Expected closing parenthesis for procedure parameters")
        self.consume(TokenType.RIGHTARROW, "Expected right arrow after procedure parameters")
        return_type = ast_.Type_(self.expr())
        self.consume(TokenType.COLON, "Expected colon after procedure type")
        block = self.block()
        return ast_.ProcedureDef(name, params, block, return_type)

    @store_derivation
    def typed_name(self) -> ast_.TypedName:
        t = self.advance()
        if t.type_ != TokenType.IDENTIFIER:
            self.error("Expected identifier for typed name")
        name = ast_.Identifier(t.value)

        if self.match(TokenType.COLON):
            type_annotation = self.expr()
            return ast_.TypedName(name, ast_.Type_(type_annotation))
        return ast_.TypedName(name, ast_.None_())

    @store_derivation
    def block(self) -> ast_.Statements:
        if self.peek().type_ != TokenType.NEWLINE:
            return ast_.Statements([self.simple_stmt()])

        self.consume(TokenType.NEWLINE, "Expected newline for block")
        self.consume(TokenType.INDENT, "Expected indentation for block")
        statements = self.statements()
        self.consume(TokenType.DEDENT, "Expected dedentation for block")
        return statements


def parse(source_text: str) -> ast_.Start:
    """Parse a list of tokens into an abstract syntax tree (AST)."""
    tokens = scan(source_text)
    parser = Parser(tokens, source_text)
    res = parser.start()

    if not parser.errors:
        return res

    raise ParseError(parser)
