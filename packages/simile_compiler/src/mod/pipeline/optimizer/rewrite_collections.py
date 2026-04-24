from __future__ import annotations
import ast
from typing import Callable, Sequence
from dataclasses import dataclass, field
from copy import deepcopy

from loguru import logger

from src.mod.data import ast_
from src.mod.pipeline import analysis
from src.mod.pipeline.optimizer.rewrite_collection import RewriteCollection
from src.mod.pipeline.optimizer.intermediate_ast import (
    GeneratorSelection,
    CombinedGeneratorSelection,
    SingleGeneratorSelection,
    Loop,
)

# NOTE: REWRITE RULES MUST ALWAYS USE THE PARENT FORM FOR STRUCTURAL MATCHING (ex. BinaryOp instead of Add)


@dataclass
class SyntacticSugarForBags(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.bag_image,
            self.bag_predicate_operations,
        ]

    def bag_image(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Image(r, b):
                if not ast_.SetType.is_relation(r.get_type):
                    logger.warning(f"First argument to bag image {r} is not a relation")
                    return None
                if not ast_.SetType.is_bag(b.get_type):
                    logger.warning(f"Second argument to bag image {b} is not a bag")
                    return None
                return ast_.Composition(ast_.Inverse(r), b)
        return None

    def bag_predicate_operations(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            # Idea, if we want to add some compilation-time optimizations (like union of two set enums into one set enum),
            # we can just add those rules here
            case ast_.BinaryOp(left, right, op_type) if op_type in (
                ast_.BinaryOperator.UNION,
                ast_.BinaryOperator.INTERSECTION,
                ast_.BinaryOperator.ADD,
                ast_.BinaryOperator.DIFFERENCE,  # TODO fix, see below
            ):
                # if not ast_.SetType.is_set(left.get_type) or not ast_.SetType.is_set(right.get_type):
                #     logger.debug(f"FAILED: at least one union child is not a set type: {left.get_type}, {right.get_type}")
                #     return None

                if not ast_.SetType.is_bag(left.get_type) or not ast_.SetType.is_bag(right.get_type):
                    logger.debug(f"FAILED: Both operands must be bags")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                match op_type:
                    case (
                        ast_.BinaryOperator.DIFFERENCE
                    ):  # TODO this should really be subtract - different from set difference. this is just to get the warehouse example working with the existing type system - type system should be revised first
                        logger.debug("WARNING: Subtracting bags not fully correctly implemented (subtraction doesn't work)")
                        # TODO see if this method is more efficient?
                        new_ast = ast_.BagComprehension(
                            ast_.And(
                                [
                                    ast_.In(
                                        maplet.left,
                                        ast_.Call(ast_.Identifier("dom"), [left]),
                                    ),
                                    ast_.Equal(
                                        maplet.right,
                                        ast_.Subtract(
                                            ast_.Call(left, [maplet.left]),
                                            ast_.Call(
                                                ast_.Union(
                                                    right,
                                                    ast_.BagEnumeration(
                                                        [
                                                            ast_.Maplet(maplet.left, ast_.Int("0")),
                                                        ]
                                                    ),
                                                ),
                                                [maplet.left],
                                            ),
                                        ),
                                    ),
                                    ast_.GreaterThan(maplet.right, ast_.Int("0")),
                                ]
                            ),
                            maplet,
                        )
                        new_ast._bound_identifiers = {maplet.left}
                        return new_ast
                    case ast_.BinaryOperator.UNION:
                        func_name = "max"
                        generator = ast_.In(
                            maplet.left,
                            ast_.Union(
                                ast_.Call(ast_.Identifier("dom"), [left]),
                                ast_.Call(ast_.Identifier("dom"), [right]),
                            ),
                        )
                        additional_cond: ast_.ASTNode = ast_.True_()
                    case ast_.BinaryOperator.ADD:
                        func_name = "sum"
                        generator = ast_.In(
                            maplet.left,
                            ast_.Union(
                                ast_.Call(ast_.Identifier("dom"), [left]),
                                ast_.Call(ast_.Identifier("dom"), [right]),
                            ),
                        )
                        additional_cond = ast_.True_()
                    case ast_.BinaryOperator.INTERSECTION:
                        func_name = "min"
                        generator = ast_.In(
                            maplet.left,
                            ast_.Intersection(
                                ast_.Call(ast_.Identifier("dom"), [left]),
                                ast_.Call(ast_.Identifier("dom"), [right]),
                            ),
                        )
                        additional_cond = ast_.GreaterThan(maplet.right, ast_.Int("0"))

                new_ast = ast_.BagComprehension(
                    ast_.And(
                        [
                            generator,
                            ast_.Equal(
                                maplet.left,
                                ast_.Call(
                                    ast_.Identifier(func_name),
                                    [
                                        ast_.Union(
                                            ast_.Image(left, maplet.left),
                                            ast_.Image(right, maplet.left),
                                        ),
                                    ],
                                ),
                            ),
                            additional_cond,
                        ]
                    ),
                    maplet,
                )
                new_ast._bound_identifiers = {maplet.left}
                return new_ast
        return None


@dataclass
class SyntacticSugarForSequences(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.concat,
            self.flatten,
            self.foldL,
            self.first,
            self.tail,
            self.append,
            self.prepend,
        ]

    def concat(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(seq1, seq2, ast_.BinaryOperator.CONCAT):
                if not ast_.SetType.is_sequence(seq1.get_type) or not ast_.SetType.is_sequence(seq2.get_type):
                    logger.warning(f"Arguments to concat {seq1}, {seq2} are not sequences")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )
                updated_index_seq2 = ast_.Identifier(self._get_fresh_identifier_name())

                seq2_with_updated_indices = ast_.SequenceComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, seq2),
                            ast_.Equal(
                                updated_index_seq2,
                                ast_.Add(
                                    maplet.left,
                                    ast_.Call(
                                        ast_.Identifier("max"),
                                        [
                                            ast_.Call(
                                                ast_.Identifier("dom"),
                                                [seq1],
                                            )
                                        ],
                                    ),
                                ),
                            ),
                        ]
                    ),
                    ast_.MapletIdentifier(
                        updated_index_seq2,
                        maplet.right,
                    ),
                )
                seq2_with_updated_indices._bound_identifiers = {maplet}

                return ast_.Union(
                    seq1,
                    seq2_with_updated_indices,
                )
        return None

    def flatten(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("flatten"), [seq]):
                if not ast_.SetType.is_sequence(seq.get_type) or not ast_.SetType.is_sequence(seq.get_type.element_type):
                    logger.warning(f"Argument to flatten {seq} is not a sequence of sequences")
                    return None

                return ast_.Call(
                    ast_.Identifier("foldL"),
                    [ast_.Identifier("concat"), ast_.SequenceEnumeration([]), seq],
                )

        return None

    def foldL(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("foldL"), [func, initial, []]):
                return initial
            case ast_.Call(ast_.Identifier("foldL"), [func, initial, seq]):
                if not ast_.SetType.is_sequence(seq.get_type):
                    logger.warning(f"Argument to foldL {seq} is not a sequence")
                    return None

                return ast_.Call(
                    ast_.Identifier("foldL"),
                    [
                        func,
                        ast_.Call(func, [initial, ast_.Call(ast_.Identifier("first"), [seq])]),
                        ast_.Call(ast_.Identifier("tail"), [seq]),
                    ],
                )

        return None

    def first(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("first"), [seq]):
                if not ast_.SetType.is_sequence(seq.get_type):
                    logger.warning(f"Argument to first {seq} is not a sequence")
                    return None

                return ast_.Call(seq, [ast_.Int("0")])

        return None

    def tail(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("tail"), [seq]):
                if not ast_.SetType.is_sequence(seq.get_type):
                    logger.warning(f"Argument to tail {seq} is not a sequence")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )
                decreased_left_side = ast_.Identifier(self._get_fresh_identifier_name())

                tail_comprehension = ast_.SetComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, seq),
                            ast_.NotEqual(
                                maplet.left,
                                ast_.Int("0"),
                            ),
                            ast_.Equal(
                                decreased_left_side,
                                ast_.Subtract(maplet.left, ast_.Int("1")),
                            ),
                        ]
                    ),
                    ast_.MapletIdentifier(
                        decreased_left_side,
                        maplet.right,
                    ),
                )
                tail_comprehension._bound_identifiers = {maplet}

                return tail_comprehension

        return None

    def append(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("append"), [seq, element]):
                if not ast_.SetType.is_sequence(seq.get_type):
                    logger.warning(f"First argument to append {seq} is not a sequence")
                    return None

                if seq.get_type.element_type.right != element.get_type:
                    logger.warning(f"Second argument to append {element} does not match type of list element")
                    return None

                return ast_.Union(
                    seq,
                    ast_.SequenceEnumeration(
                        [
                            ast_.Maplet(
                                ast_.Call(
                                    ast_.Identifier("max"),
                                    [
                                        ast_.Call(
                                            ast_.Identifier("dom"),
                                            [seq],
                                        )
                                    ],
                                ),
                                element,
                            ),
                        ]
                    ),
                )

        return None

    def prepend(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("prepend"), [seq, element]):
                if not ast_.SetType.is_sequence(seq.get_type):
                    logger.warning(f"First argument to prepend {seq} is not a sequence")
                    return None

                if seq.get_type.element_type.right != element.get_type:
                    logger.warning(f"Second argument to prepend {element} does not match type of list element")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )
                increased_left_side = ast_.Identifier(self._get_fresh_identifier_name())

                return ast_.Union(
                    ast_.SequenceEnumeration(
                        [
                            ast_.Maplet(
                                ast_.Int("0"),
                                element,
                            ),
                        ]
                    ),
                    ast_.SequenceComprehension(
                        ast_.And(
                            [
                                ast_.In(maplet, seq),
                                ast_.Equal(
                                    increased_left_side,
                                    ast_.Add(maplet.left, ast_.Int("1")),
                                ),
                            ]
                        ),
                        ast_.MapletIdentifier(
                            increased_left_side,
                            maplet.right,
                        ),
                    ),
                )

        return None


@dataclass
class BuiltinFunctions(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.functional_override,
            self.cardinality,
            self.domain,
            self.range_,
            self.override,
            self.range_restriction,
            self.range_subtraction,
            self.domain_restriction,
            self.domain_subtraction,
        ]

    def functional_override(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Assignment(ast_.Call(f, [x]), value) if ast_.SetType.is_relation(f.get_type):
                if f.get_type.element_type.left != x.get_type:
                    logger.warning(f"Argument to functional override {x} does not match type of relation element")
                    return None

                return ast_.Assignment(
                    f,
                    ast_.RelationOverriding(
                        f,
                        ast_.RelationEnumeration(
                            [
                                ast_.Maplet(x, value),
                            ],
                        ),
                    ),
                    [],
                    False,
                )
        return None

    def cardinality(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("card"), [s]):
                if not ast_.SetType.is_set(s.get_type):
                    logger.warning(f"Argument to cardinality {s} is not a set")
                    return None

                fresh_variable = ast_.Identifier(self._get_fresh_identifier_name())
                ast_sum = ast_.Sum(
                    ast_.And([ast_.In(fresh_variable, s)]),
                    ast_.Int("1"),
                )
                ast_sum._bound_identifiers = {fresh_variable}
                return ast_sum
        return None

    def domain(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("dom"), [relation]):
                if not ast_.SetType.is_set(relation.get_type):
                    logger.warning(f"Argument to domain {relation} is not a set")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                new_ast = ast_.SetComprehension(
                    ast_.And([ast_.In(maplet, relation)]),
                    maplet.left,
                )
                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None

    def range_(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("ran"), [relation]):
                if not ast_.SetType.is_set(relation.get_type):
                    logger.warning(f"Argument to range {relation} is not a set")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                new_ast = ast_.SetComprehension(
                    ast_.And([ast_.In(maplet, relation)]),
                    maplet.right,
                )
                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None

    def domain_restriction(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                left,
                right,
                ast_.BinaryOperator.DOMAIN_RESTRICTION,
            ):
                if not ast_.SetType.is_set(left.get_type):
                    logger.debug(f"FAILED: left side of domain restriction is not a set type: {left.get_type}")
                    return None
                if not ast_.SetType.is_relation(right.get_type):
                    logger.debug(f"FAILED: right side of domain restriction is not a relation type: {right.get_type}")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                new_ast = ast_.RelationComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, right),
                            ast_.In(maplet.left, left),
                        ],
                    ),
                    maplet,
                )

                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None

    def domain_subtraction(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                left,
                right,
                ast_.BinaryOperator.DOMAIN_SUBTRACTION,
            ):
                if not ast_.SetType.is_set(left.get_type):
                    logger.debug(f"FAILED: left side of domain subtraction is not a set type: {left.get_type}")
                    return None

                if not ast_.SetType.is_relation(right.get_type):
                    logger.debug(f"FAILED: right side of domain subtraction is not a relation type: {right.get_type}")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                new_ast = ast_.RelationComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, right),
                            ast_.NotIn(maplet.left, left),
                        ],
                    ),
                    maplet,
                )
                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None

    def range_restriction(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                left,
                right,
                ast_.BinaryOperator.RANGE_RESTRICTION,
            ):
                if not ast_.SetType.is_set(right.get_type):
                    logger.debug(f"FAILED: left side of range restriction is not a set type: {right.get_type}")
                    return None
                if not ast_.SetType.is_relation(left.get_type):
                    logger.debug(f"FAILED: right side of range restriction is not a relation type: {left.get_type}")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                new_ast = ast_.RelationComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, left),
                            ast_.In(maplet.left, right),
                        ],
                    ),
                    maplet,
                )
                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None

    def range_subtraction(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                left,
                right,
                ast_.BinaryOperator.RANGE_SUBTRACTION,
            ):
                if not ast_.SetType.is_set(right.get_type):
                    logger.debug(f"FAILED: left side of range subtraction is not a set type: {right.get_type}")
                    return None
                if not ast_.SetType.is_relation(left.get_type):
                    logger.debug(f"FAILED: right side of range subtraction is not a relation type: {left.get_type}")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                new_ast = ast_.RelationComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, left),
                            ast_.NotIn(maplet.left, right),
                        ],
                    ),
                    maplet,
                )
                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None

    def override(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                left,
                right,
                ast_.BinaryOperator.RELATION_OVERRIDING,
            ):
                return ast_.Union(
                    left,
                    ast_.DomainSubtraction(
                        ast_.Call(ast_.Identifier("dom"), [left]),
                        right,
                    ),
                )
        return None

    def sum(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("sum"), [arg]):
                if not ast_.SetType.is_set(arg.get_type):
                    logger.debug(f"FAILED: argument of sum is not a set type: {arg.get_type}")
                    return None
                if not isinstance(arg.get_type.element_type, ast_.BaseSimileType) or not arg.get_type.element_type.is_numeric():
                    logger.debug(f"FAILED: element type of sum argument is not a numeric type: {arg.get_type.element_type}")
                    return None

                iterator = ast_.Identifier(self._get_fresh_identifier_name())
                new_ast = ast_.Sum(
                    ast_.And([ast_.In(iterator, arg)]),
                    iterator,
                )
                new_ast._bound_identifiers = {iterator}
                return new_ast
        return None

    def bag_size(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(ast_.Identifier("size"), [arg]):
                if not ast_.SetType.is_bag(arg.get_type):
                    logger.debug(f"FAILED: argument of size is not a bag type: {arg.get_type}")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )
                new_ast = ast_.Sum(
                    ast_.And([ast_.In(maplet, arg)]),
                    maplet.right,
                )
                new_ast._bound_identifiers = {maplet}
                return new_ast
        return None


@dataclass
class InsideQuantifierRewriteCollection(RewriteCollection):
    bound_quantifier_variables: set[ast_.Identifier] = field(default_factory=set)
    current_bound_identifiers: list[set[ast_.Identifier | ast_.MapletIdentifier]] = field(default_factory=list)

    def apply_all_rules_one_traversal(self, ast):
        bound_quantifier_variables_before = deepcopy(self.bound_quantifier_variables)
        if isinstance(ast, ast_.Quantifier):
            logger.debug(f"Quantifier found with bound variables: {ast.bound}")
            self.bound_quantifier_variables |= ast.flatten_bound_identifiers()
            self.current_bound_identifiers.append(ast._bound_identifiers)

        ast = super().apply_all_rules_one_traversal(ast)

        self.bound_quantifier_variables = bound_quantifier_variables_before
        if self.current_bound_identifiers and hasattr(ast, "_bound_identifiers"):
            if ast._bound_identifiers != self.current_bound_identifiers:  # type: ignore
                logger.debug(f"Restoring (replacing) bound identifiers for AST node: {ast._bound_identifiers} with {self.current_bound_identifiers[-1]}")  # type: ignore
                # If the current bound identifiers are set, we need to update the AST's bound identifiers
                ast._bound_identifiers = self.current_bound_identifiers.pop()  # type: ignore
            else:
                self.current_bound_identifiers.pop()
        return ast

    def inside_quantifier(self) -> bool:
        if self.bound_quantifier_variables:
            return True
        return False


@dataclass
class ComprehensionConstructionCollection(InsideQuantifierRewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.functional_image,
            self.image,
            self.product,
            self.inverse,
            self.composition,
            self.set_predicate_operations,
            self.membership_collapse,
            self.dummy_variable_replacing,
        ]

    def functional_image(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Call(
                rel,
                [arg],
            ) if isinstance(
                rel.get_type, ast_.SetType
            ) and ast_.SetType.is_relation(rel.get_type):
                if rel.get_type.relation_subtype is None:
                    logger.debug(f"FAILED: relation {rel} does not have a functional subtype - functional image may be undefined (disabled for now)")
                    return None
                if not rel.get_type.relation_subtype.total:
                    logger.debug(f"FAILED: relation {rel} is not total - functional image may return nothing (disabled for now)")
                    return None
                if not rel.get_type.relation_subtype.one_to_many:
                    logger.debug(f"FAILED: relation {rel} is not one-to-many - functional image may return multiple values (disabled for now)")
                    return None

                return ast_.Call(ast_.Identifier("choice"), [ast_.Image(rel, arg)])

        return None

    def image(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Image(left, right):
                if not ast_.SetType.is_relation(left.get_type):
                    logger.debug(f"FAILED: left side of image is not a relation type: {left.get_type}")
                    return None
                if not ast_.SetType.is_set(right.get_type):
                    logger.debug(f"FAILED: right side of image is not a set type: {right.get_type}")
                    return None

                maplet = ast_.MapletIdentifier(
                    ast_.Identifier(self._get_fresh_identifier_name()),
                    ast_.Identifier(self._get_fresh_identifier_name()),
                )

                set_comprehension = ast_.SetComprehension(
                    ast_.And(
                        [
                            ast_.In(maplet, left),
                            ast_.In(maplet.left, right),
                        ]
                    ),
                    maplet.right,
                )
                set_comprehension._bound_identifiers = {maplet}

                return set_comprehension

        return None

    def product(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                ast_.MapletIdentifier((_, _)) as maplet,
                ast_.BinaryOp(left, right, ast_.BinaryOperator.CARTESIAN_PRODUCT),
                ast_.BinaryOperator.IN,
            ) if self.inside_quantifier():
                # Inside quantifier predicate check, similar to membership collapse
                if not maplet.flatten().issubset(self.bound_quantifier_variables):
                    logger.debug(f"FAILED: {maplet} appears as a generator variable but is not bound by a quantifier")
                    return None

                if not ast_.SetType.is_set(left.get_type):
                    logger.debug(f"FAILED: left side of product is not a set type: {left.get_type}")
                    return None
                if not ast_.SetType.is_set(right.get_type):
                    logger.debug(f"FAILED: right side of product is not a set type: {right.get_type}")
                    return None

                # TODO is this really the correct move? nested quantifiers may cause trouble...
                self.current_bound_identifiers[-1].remove(maplet)
                self.current_bound_identifiers[-1].update({maplet.left, maplet.right})

                return ast_.And(
                    [
                        ast_.In(maplet.left, left),
                        ast_.In(maplet.right, right),
                    ]
                )
        return None

    def inverse(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                ast_.MapletIdentifier((_, _)) as maplet,
                ast_.UnaryOp(
                    inner,
                    ast_.UnaryOperator.INVERSE,
                ),
                ast_.BinaryOperator.IN,
            ) if self.inside_quantifier():
                if not maplet.flatten().issubset(self.bound_quantifier_variables):
                    logger.debug(f"FAILED: {maplet} appears as a generator variable but is not bound by a quantifier")
                    return None

                if not ast_.SetType.is_relation(inner.get_type):
                    logger.debug(f"FAILED: inner side of inverse is not a relation type: {inner.get_type}")
                    return None

                rev_maplet: ast_.MapletIdentifier = ast_.MapletIdentifier(maplet.right, maplet.left)
                self.current_bound_identifiers[-1].remove(maplet)
                self.current_bound_identifiers[-1].update({rev_maplet})

                return ast_.In(rev_maplet, inner)
        return None

    def composition(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                ast_.MapletIdentifier((_, _)) as maplet,
                ast_.BinaryOp(
                    left,
                    right,
                    ast_.BinaryOperator.COMPOSITION,
                ),
                ast_.BinaryOperator.IN,
            ) if self.inside_quantifier():
                if not maplet.flatten().issubset(self.bound_quantifier_variables):
                    logger.debug(f"FAILED: {maplet} appears as a generator variable but is not bound by a quantifier")
                    return None

                if not ast_.SetType.is_set(left.get_type):
                    logger.debug(f"FAILED: left side of composition is not a set type: {left.get_type}")
                    return None
                if not ast_.SetType.is_set(right.get_type):
                    logger.debug(f"FAILED: right side of composition is not a set type: {right.get_type}")
                    return None

                fresh_var_left = ast_.Identifier(self._get_fresh_identifier_name())
                fresh_var_right = ast_.Identifier(self._get_fresh_identifier_name())

                maplet_left: ast_.MapletIdentifier[ast_.IdentifierListTypes, ast_.Identifier] = ast_.MapletIdentifier(maplet.left, fresh_var_left)
                maplet_right: ast_.MapletIdentifier[ast_.Identifier, ast_.IdentifierListTypes] = ast_.MapletIdentifier(fresh_var_right, maplet.right)

                self.current_bound_identifiers[-1].remove(maplet)
                self.current_bound_identifiers[-1].update({maplet_left, maplet_right})

                return ast_.And(
                    [
                        ast_.In(maplet_left, left),
                        ast_.In(maplet_right, right),
                        ast_.Equal(fresh_var_left, fresh_var_right),
                    ]
                )
        return None

    def set_predicate_operations(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            # Idea, if we want to add some compilation-time optimizations (like union of two set enums into one set enum),
            # we can just add those rules here
            case ast_.BinaryOp(left, right, op_type) if op_type in (
                ast_.BinaryOperator.UNION,
                ast_.BinaryOperator.INTERSECTION,
                ast_.BinaryOperator.DIFFERENCE,
            ):
                if not ast_.SetType.is_set(left.get_type) or not ast_.SetType.is_set(right.get_type):
                    logger.debug(f"FAILED: at least one union child is not a set type: {left.get_type}, {right.get_type}")
                    return None

                if ast_.SetType.is_bag(left.get_type) and ast_.SetType.is_bag(right.get_type):
                    logger.debug(f"FAILED: Union/Intersection/Difference operations must use bag_predicate_operations rule (both operands are bags)")
                    return None

                fresh_name = self._get_fresh_identifier_name()

                match op_type:
                    case ast_.BinaryOperator.UNION:
                        list_op: type[ast_.And | ast_.Or] = ast_.Or
                        right_join_op: type[ast_.In | ast_.NotIn] = ast_.In
                    case ast_.BinaryOperator.INTERSECTION:
                        list_op = ast_.And
                        right_join_op = ast_.In
                    case ast_.BinaryOperator.DIFFERENCE:
                        list_op = ast_.And
                        right_join_op = ast_.NotIn

                new_ast = ast_.SetComprehension(
                    list_op(
                        [
                            ast_.In(ast_.Identifier(fresh_name), left),
                            right_join_op(ast_.Identifier(fresh_name), right),
                        ],
                    ),
                    ast_.Identifier(fresh_name),
                )
                new_ast._bound_identifiers = {ast_.Identifier(fresh_name)}
                self.current_bound_identifiers.append(new_ast._bound_identifiers)  # TODO is this needed?
                return new_ast

        return None

    def membership_collapse(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(
                ast_.Identifier(_) as x,
                ast_.Quantifier(predicate, expression, op_type) as inner_quantifier,
            ) if op_type.is_collection_operator():

                # If x is not bound by a quantifier, this expression may just be an equality check (ie, is x in {1,2,3}?)
                # rather than a generator
                if self.inside_quantifier() and x not in self.bound_quantifier_variables:
                    logger.debug(f"FAILED: {x} appears as a generator variable but is not bound by a quantifier")
                    return None

                logger.debug(f"TEST: Previous current bound identifiers: {self.current_bound_identifiers[-1]}")
                self.current_bound_identifiers[-1] |= inner_quantifier._bound_identifiers
                logger.debug(f"TEST: Updated current bound identifiers: {self.current_bound_identifiers[-1]}")

                return ast_.And(
                    [
                        ast_.Equal(x, expression),
                        predicate,
                    ],
                )
        return None

    def dummy_variable_replacing(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            # TODO make rule accept top-level ORs
            # Had an issue getting this to work with top level ORs, as a dummy variable may be replaceable in one or-clause but not the other
            # Ex: {x | x in A or (x = y and y |-> z in B)} - here, we can sub in dummy x for y |-> z in the second clause but not the first
            # This is kind-of a hack, but we need to handle extra variables created by membership collapse - see visitor info system as an example
            case ast_.Quantifier(
                predicate,
                expression,
                op_type,
            ):
                if predicate.op_type != ast_.ListOperator.AND:
                    logger.warning("FAILED: dummy variable replacing only works with AND predicates currently, TODO for ORs")
                    return None

                flattened_bound_identifiers_with_guaranteed_generators = set()
                new_bound_identifiers = set()

                # Identify which bound variables actually have generators
                for bound_identifier in ast._bound_identifiers:
                    for predicate_item in predicate.items:
                        # if isinstance(predicate_item, ast_.In) and isinstance(predicate_item.left, ast_.IdentifierListTypes) and bound_identifier in predicate_item.left.flatten():
                        if isinstance(predicate_item, ast_.In):
                            if isinstance(predicate_item.left, ast_.IdentifierListTypes):
                                if bound_identifier in predicate_item.left.flatten() | {predicate_item.left}:
                                    flattened_bound_identifiers_with_guaranteed_generators |= bound_identifier.flatten()
                                    new_bound_identifiers.add(bound_identifier)
                                    break
                logger.debug(f"TEST: flattened_bound_identifiers_with_guaranteed_generators: {flattened_bound_identifiers_with_guaranteed_generators}")
                logger.debug(f"TEST: new_bound_identifiers: {new_bound_identifiers}")
                logger.debug(f"TEST: ast._bound_identifiers: {ast._bound_identifiers}")

                if ast._bound_identifiers == new_bound_identifiers:
                    logger.warning("SKIP: All bound identifiers have generators, no dummy variables to replace")
                    return None

                # Attempt to eliminate bound identifiers that are only bound by equality
                # We use simple substitution for them
                for bound_identifier in ast._bound_identifiers - flattened_bound_identifiers_with_guaranteed_generators:
                    assert isinstance(predicate, ast_.ListOp), "Predicate must be a ListOp - check that find and replace did not ruin it"
                    for predicate_item in predicate.items:
                        if isinstance(predicate_item, ast_.Equal):
                            if predicate_item.left == bound_identifier and predicate_item.right in flattened_bound_identifiers_with_guaranteed_generators:
                                predicate.items.remove(predicate_item)
                                predicate = predicate.find_and_replace(bound_identifier, predicate_item.right)  # type: ignore
                                expression = expression.find_and_replace(bound_identifier, predicate_item.right)
                                break
                            elif predicate_item.right == bound_identifier and predicate_item.left in flattened_bound_identifiers_with_guaranteed_generators:
                                predicate.items.remove(predicate_item)
                                predicate = predicate.find_and_replace(bound_identifier, predicate_item.left)  # type: ignore
                                expression = expression.find_and_replace(bound_identifier, predicate_item.left)
                                break

                assert isinstance(predicate, ast_.ListOp), "Predicate must be a ListOp - check that find and replace did not ruin it"
                new_ast = ast_.Quantifier(
                    predicate,
                    expression,
                    op_type,
                )
                new_ast._bound_identifiers = new_bound_identifiers
                self.current_bound_identifiers.pop()  # Remove old bound identifiers
                self.current_bound_identifiers.append(new_ast._bound_identifiers)
                return new_ast
        return None


@dataclass
class DisjunctiveNormalFormCollection(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.double_negation,
            self.distribute_de_morgan,
            self.distribute,
            self.flatten_nested_ands,
            self.flatten_nested_ors,
        ]

    def flatten_nested_ands(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.ListOp(elems, ast_.ListOperator.AND):
                if not any(map(lambda x: isinstance(x, ast_.ListOp) and x.op_type == ast_.ListOperator.AND, elems)):
                    return None
                return ast_.And(elems)

        return None

    def flatten_nested_ors(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.ListOp(elems, ast_.ListOperator.OR):
                if not any(map(lambda x: isinstance(x, ast_.ListOp) and x.op_type == ast_.ListOperator.OR, elems)):
                    return None
                return ast_.Or(elems)

        return None

    def double_negation(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.UnaryOp(
                ast_.UnaryOp(
                    x,
                    ast_.UnaryOperator.NOT,
                ),
                ast_.UnaryOperator.NOT,
            ):
                return x
        return None

    def distribute_de_morgan(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.UnaryOp(
                ast_.ListOp(elems, ast_.ListOperator.OR),
                ast_.UnaryOperator.NOT,
            ):
                return ast_.And(
                    [ast_.UnaryOp(elem, ast_.UnaryOperator.NOT) for elem in elems],
                )
            case ast_.UnaryOp(
                ast_.ListOp(elems, ast_.ListOperator.AND),
                ast_.UnaryOperator.NOT,
            ):
                return ast_.Or(
                    [ast_.UnaryOp(elem, ast_.UnaryOperator.NOT) for elem in elems],
                )
        return None

    def distribute(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.ListOp(elems, ast_.ListOperator.AND):
                if not any(map(lambda x: isinstance(x, ast_.ListOp) and x.op_type == ast_.ListOperator.OR, elems)):
                    return None

                or_elems: list[ast_.ListOp] = []
                non_or_elems: list[ast_.ASTNode] = []

                for elem in elems:
                    if isinstance(elem, ast_.ListOp) and elem.op_type == ast_.ListOperator.OR:
                        or_elems.append(elem)
                    else:
                        non_or_elems.append(elem)

                if not or_elems:
                    # Not really a failure, more of a matching refinement
                    logger.debug("FAILED: no OR elements found in AND list operation - this message should be caught beforehand")
                    return None

                new_elems: list[ast_.ASTNode] = []
                or_elem_to_distribute = or_elems[0]
                # Very inefficient, but basically just distribute one or element at a time
                # Calling rewrite rules repeatedly will handle the rest
                non_or_elems = non_or_elems + or_elems[1:]  # type: ignore
                for item in or_elem_to_distribute.items:
                    new_elems.append(ast_.And([item] + non_or_elems))

                return ast_.Or(new_elems)

        return None


@dataclass
class OrWrappingCollection(RewriteCollection):
    def _rewrite_collection(self):
        return [
            self.or_wrapping,
        ]

    def or_wrapping(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Quantifier(ast_.ListOp(_, ast_.ListOperator.AND) as elem, expression, op_type):
                new_quantifier = ast_.Quantifier(
                    ast_.Or([elem]),
                    expression,
                    op_type,
                )
                new_quantifier._bound_identifiers = ast._bound_identifiers
                return new_quantifier
            case ast_.Quantifier(ast_.ListOp(_, ast_.ListOperator.OR) as elem, expression, op_type):
                return None
            case ast_.Quantifier(elem, expression, op_type):
                new_quantifier = ast_.Quantifier(
                    ast_.And([elem]),
                    expression,
                    op_type,
                )
                new_quantifier._bound_identifiers = ast._bound_identifiers
                return new_quantifier

        return None


@dataclass
class GeneratorSelectionCollection(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.gsp_wrapping,
            self.nested_generator_selection,
        ]

    def gsp_wrapping(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        # TODO does this get the nested case too?...
        match ast:
            case ast_.Quantifier(
                ast_.ListOp(elems, ast_.ListOperator.OR),
                expression,
                op_type,
            ):

                if ast._env is None:
                    logger.debug(f"FAILED: no environment found in quantifier (cannot choose generators)")
                    return None

                if all(map(lambda x: isinstance(x, GeneratorSelection) or isinstance(x, CombinedGeneratorSelection), elems)):
                    logger.debug(f"FAILED: all elements in OR quantifier are already GeneratorSelections, no need to select generators")
                    return None

                gsps: list[GeneratorSelection | ast_.ASTNode] = []
                for elem in elems:
                    if not isinstance(elem, ast_.ListOp) or elem.op_type != ast_.ListOperator.AND:
                        logger.debug(f"FAILED: element in OR quantifier is not an And operation (got {elem})")
                        return None

                    gsp = self._make_gsp_from_and_clause(elem.items, ast._bound_identifiers)
                    if gsp is None:
                        logger.debug(f"FAILED: could not make GSP from and clause {elem} with bound identifiers {ast._bound_identifiers}")
                        return None

                    gsps.append(gsp)

                if not gsps:
                    logger.debug(f"FAILED: no valid generator selections found in OR quantifier (got {elems})")
                    return None

                # No _bound_identifiers from this point on?
                ret = ast_.Quantifier(
                    ast_.Or(gsps),
                    expression,
                    op_type,
                )
                ret._bound_identifiers = ast._bound_identifiers
                return ret
                # predicates: list[ast_.ASTNode] = []
                # generators_with_alternatives: list[list[ast_.In]] = []
                # for elem in elems:

            # This should only match once per quantifier
            # For each And inside the Or:
            # - Only match if valid generator selection:
            #   - Generator structure exists with LHS in _bound_identifiers
            # - Then:
            #   - Only one generator per bound identifier - need to find all alternatives and then restrict from there
            #   - Try to order in list as a composition chain
        return None

    def _make_gsp_from_and_clause(
        self,
        and_clause: list[ast_.ASTNode],
        bound_identifiers: set[ast_.Identifier | ast_.MapletIdentifier],
    ) -> GeneratorSelection | None:
        candidate_generators_per_identifier: dict[ast_.Identifier | ast_.MapletIdentifier, list[ast_.In]] = {identifier: [] for identifier in bound_identifiers}
        other_predicates: list[ast_.ASTNode] = []
        for elem in and_clause:
            if not isinstance(elem, ast_.BinaryOp):
                other_predicates.append(elem)
                continue
            if any(
                [
                    elem.op_type != ast_.BinaryOperator.IN,
                    not isinstance(elem.left, ast_.Identifier | ast_.MapletIdentifier),
                    elem.left not in candidate_generators_per_identifier,
                    not ast_.SetType.is_set(elem.right.get_type),
                ]
            ):
                other_predicates.append(elem)
                continue

            assert isinstance(elem.left, ast_.Identifier | ast_.MapletIdentifier)
            casted_elem = ast_.In(elem.left, elem.right)
            candidate_generators_per_identifier[elem.left].append(casted_elem)

        # Ensure every identifier has at least one suitable generator
        for identifier, candidate_generators in candidate_generators_per_identifier.items():
            if len(candidate_generators) == 0:
                logger.debug(f"Failed to find a suitable generator for identifier {identifier}. Dict of generators: {candidate_generators_per_identifier}")
                return None

        identifiers: set[ast_.Identifier] = set(filter(lambda x: isinstance(x, ast_.Identifier), bound_identifiers))  # type: ignore
        # There may be more than one chain, chains will contain a sequence of MapletIdentifiers
        maplets: set[ast_.MapletIdentifier] = set(filter(lambda x: isinstance(x, ast_.MapletIdentifier), bound_identifiers))  # type: ignore
        maplet_chains: list[list[ast_.MapletIdentifier]] = []

        while maplets:
            maplet = maplets.pop()
            # Each maplet should only occur once, and only be added to a chain once (variable names are guaranteed to be unique)

            for i in range(len(maplet_chains)):
                if any(
                    [
                        maplet.left == maplet_chains[i][-1].right,
                        ast_.Equal(maplet.left, maplet_chains[i][-1].right) in other_predicates,
                        ast_.Equal(maplet_chains[i][-1].right, maplet.left) in other_predicates,
                    ]
                ):
                    maplet_chains[i].append(maplet)
                    break

                if any(
                    [
                        maplet.right == maplet_chains[i][0].left,
                        ast_.Equal(maplet.right, maplet_chains[i][0].left) in other_predicates,
                        ast_.Equal(maplet_chains[i][0].left, maplet.right) in other_predicates,
                    ]
                ):
                    maplet_chains[i].insert(0, maplet)
                    break
            else:
                maplet_chains.append([maplet])

        # TODO make a proper ordering for this, base on size, relation subtype, etc.
        generators = []
        # For now, take the longest chain first
        sorted_maplet_chains = sorted(maplet_chains, key=lambda chain: len(chain), reverse=True)
        for maplet_chain in sorted_maplet_chains:
            for maplet in maplet_chain:
                generators.append(candidate_generators_per_identifier[maplet].pop())
        for identifier in identifiers:
            generators.append(candidate_generators_per_identifier[identifier].pop())

        for unselected_candidate_generators in candidate_generators_per_identifier.values():
            other_predicates.extend(list(unselected_candidate_generators))

        return GeneratorSelection(generators, ast_.And(other_predicates))

    def nested_generator_selection(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.ListOp(elems, ast_.ListOperator.OR):
                # if all(map(lambda x: isinstance(x, GeneratorSelection) or isinstance(x, CombinedGeneratorSelection), elems)):
                #     logger.debug(f"FAILED: all elements in OR quantifier are already GeneratorSelections, no need to select generators")
                #     return None

                # Hack to use ast_.In as a dict key - use its temporary freeze hash - DONT MODIFY THE AST NODE DURING THIS PROCESS
                generator_reference_dict: dict[int, ast_.In] = {}
                combination_dict: dict[int, list[GeneratorSelection | CombinedGeneratorSelection]] = {}
                for elem in elems:
                    match elem:
                        case GeneratorSelection(generators, predicates):
                            generator_reference_dict[generators[0].temporary_freeze_hash()] = generators[0]

                            if not combination_dict.get(generators[0].temporary_freeze_hash()):
                                combination_dict[generators[0].temporary_freeze_hash()] = []
                            combination_dict[generators[0].temporary_freeze_hash()].append(
                                GeneratorSelection(
                                    generators[1:],
                                    predicates,
                                )
                            )
                        case CombinedGeneratorSelection(generator, child_generators):
                            generator_reference_dict[generator.temporary_freeze_hash()] = generator

                            if not combination_dict.get(generator.temporary_freeze_hash()):
                                combination_dict[generator.temporary_freeze_hash()] = []
                            combination_dict[generator.temporary_freeze_hash()].extend(child_generators.items)  # type: ignore
                        case _:
                            logger.debug(f"FAILED: element is not a valid GeneratorSelection or CombinedGeneratorSelection (got {elem})")
                            return None

                if len(elems) != len([y for x in combination_dict.values() for y in x]):
                    logger.debug("FAILED: some elements were not added to combination dict - this should not happen")
                    return None

                combined_generators: list[ast_.ASTNode] = []
                for combined_generator, generator_list in combination_dict.items():
                    assert isinstance(generator_reference_dict[combined_generator].left, ast_.IdentifierListTypes), "Combined generator should have an identifier on the left side"

                    # If the generator list only has one entry, we didn't combine anything - recreate the original GeneratorSelectionV2
                    if len(generator_list) == 1 and isinstance(
                        generator_list[0], GeneratorSelection
                    ):  # TODO only added this extre condition for the typechecker - double check that we only want generator selections here
                        combined_generators.append(
                            GeneratorSelection(
                                [generator_reference_dict[combined_generator]] + generator_list[0].generators,
                                generator_list[0].predicates,
                            )
                        )
                        continue

                    # Actually combine generators that need to be combined. Note that this may end up
                    # creating GeneratorSelections without a generator.
                    combined_generators.append(
                        CombinedGeneratorSelection(
                            generator_reference_dict[combined_generator],
                            ast_.Or(generator_list),  # type: ignore
                        )
                    )

                if combined_generators == elems:
                    logger.debug("FAILED: no generators were combined (likely there was nothing to combine, so this skip is expected)")
                    return None

                return ast_.Or(combined_generators)

            # Only match if all elems are either GeneratorSelectionV2 or CombinedGeneratorSelection
            # Check all elements for matches:
            # - elements that share a generator are placed in a combinedgeneratorselection
            # - predicates set to True/None
        return None


@dataclass
class GSPToLoopsCollection(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            # self.quantifier_generation,
            self.summation,
            self.top_level_or_loop,
            self.chained_gsp_loop,
            # self.empty_gsp_loop, # inlined with chained_gsp_loop
            self.combined_gsp_loop,
        ]

    def quantifier_generation(
        self,
        ast: ast_.ASTNode,
        op_type: ast_.QuantifierOperator,
        identity: ast_.ASTNode,
        accumulator: Callable[[ast_.ASTNode, ast_.ASTNode], ast_.ASTNode],
        accumulator_type: ast_.SimileType,
        accumulator_target: ast_.Identifier | None = None,
    ) -> ast_.ASTNode | None:
        match ast:
            case ast_.Quantifier(
                predicate,  # Should be an OR[GeneratorSelection | CombinedGeneratorSelection]
                expression,
                op_type_,
            ) if (
                op_type_ == op_type
            ):
                if not isinstance(predicate, ast_.ListOp) or predicate.op_type != ast_.ListOperator.OR:
                    logger.debug(f"FAILED: predicate is not a ListOp with OR operator (got {predicate}). This should be in DNF")
                    return None
                if not all(map(lambda x: isinstance(x, GeneratorSelection) or isinstance(x, CombinedGeneratorSelection), predicate.items)):
                    logger.debug(f"FAILED: not all items in predicate are GeneratorSelections (got {predicate.items}). Elements of predicates should be GeneratorSelectionASTs")
                    return None

                if ast._env is None:
                    logger.debug(f"FAILED: no environment found in quantifier (cannot perform optimizations)")
                    return None

                if accumulator_target is None:
                    accumulator_target = ast_.Identifier(self._get_fresh_identifier_name())
                    ast._env.put(accumulator_target.name, accumulator_type)

                predicate = ast_.Or(predicate.items)

                if_statement = Loop(
                    predicate,
                    ast_.Assignment(
                        accumulator_target,
                        accumulator(accumulator_target, expression),
                        [],
                        False,
                    ),
                )
                return ast_.Statements(
                    [
                        ast_.Assignment(
                            accumulator_target,
                            identity,
                            [],
                            False,
                        ),
                        if_statement,
                    ]
                )
        return None

    def quantifier_generation_assignment(
        self,
        ast: ast_.ASTNode,
        op_type: ast_.QuantifierOperator,
        identity: ast_.ASTNode,
        accumulator: Callable[[ast_.ASTNode, ast_.ASTNode], ast_.ASTNode],
        accumulator_type: ast_.SimileType,
    ) -> ast_.ASTNode | None:
        match ast:
            case ast_.Assignment(
                ast_.Identifier(_) as target,
                ast_.Quantifier(_, _, _) as quantifier,
            ):
                return self.quantifier_generation(
                    quantifier,
                    op_type,
                    identity,
                    accumulator,
                    accumulator_type,
                    target,
                )
            # case ast_.Quantifier(_, _, _):
            #     return self.quantifier_generation(
            #         ast,
            #         op_type,
            #         identity,
            #         accumulator,
            #         accumulator_type,
            #     )
        return None

    def summation(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        return self.quantifier_generation_assignment(
            ast,
            ast_.QuantifierOperator.SUM,
            ast_.Int("0"),
            ast_.Add,
            ast_.BaseSimileType.Int,
        )

    def top_level_or_loop(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case Loop(
                ast_.ListOp(generators, ast_.ListOperator.OR),
                body,
            ):
                if not all(map(lambda x: isinstance(x, GeneratorSelection) or isinstance(x, CombinedGeneratorSelection), generators)):
                    logger.debug(f"FAILED: all elements in top level OR predicate expected to be GeneratorSelections (got {generators}).")
                    return None

                statements: list[ast_.ASTNode] = []
                used_generators: list[ast_.ASTNode] = []
                for generator in generators:
                    assert isinstance(generator, GeneratorSelection | CombinedGeneratorSelection)
                    if used_generators:
                        generator.predicates = ast_.And([generator.predicates, ast_.Not(ast_.Or(used_generators))])
                    else:
                        generator.predicates = ast_.And([generator.predicates])

                    statements.append(Loop(generator, deepcopy(body)))
                    used_generators.append(generator.flatten())

                return ast_.Statements(statements)

        return None

    def chained_gsp_loop(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            # Inline empty_gsp_loop rule
            case Loop(
                GeneratorSelection([], predicates),
                body,
            ):
                return ast_.If(predicates, body)
            case Loop(
                GeneratorSelection(generators, predicates),
                body,
            ):
                if ast._env is None:
                    logger.debug(f"FAILED: no environment found in loop (cannot perform optimizations)")
                    return None

                free_predicates = []
                bound_predicates = []
                identifiers_within_child_generators: list[ast_.Identifier] = ast_.flatten(map(lambda x: x.left.find_all_instances(ast_.Identifier), generators[1:]))
                for predicate in predicates.items:
                    identifiers_within_predicate = predicate.find_all_instances(ast_.Identifier)

                    for identifier in identifiers_within_predicate:
                        if (
                            # If the identifier is not bound outside of the quantifier (and is not the current bound quantifier var)
                            ast._env.get(identifier.name) is None
                            and identifier not in generators[0].left.find_all_instances(ast_.Identifier)
                            # or if it is used within a child generator
                        ) or identifier in identifiers_within_child_generators:
                            # propagate predicate to child
                            bound_predicates.append(predicate)
                            break
                    else:
                        free_predicates.append(predicate)

                assert isinstance(generators[0].left, ast_.Identifier | ast_.MapletIdentifier), "Generators should have an identifier on the left side"

                # Dont lower bound predicates if there are no child generators to pass them to (makes optimizations harder later)
                if len(generators) == 1:
                    return Loop(
                        SingleGeneratorSelection(
                            generators[0],
                            predicates,
                        ),
                        body,
                    )

                return Loop(
                    SingleGeneratorSelection(
                        generators[0],
                        ast_.And(
                            free_predicates,
                        ),
                    ),
                    Loop(
                        GeneratorSelection(
                            generators[1:],
                            ast_.And(bound_predicates),
                        ),
                        body,
                    ),
                )

        return None

    def combined_gsp_loop(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case Loop(
                CombinedGeneratorSelection(
                    generator,
                    gsp_predicates,
                    predicates,
                ),
                body,
            ):
                child_loops: list[ast_.ASTNode] = []
                for gsp_predicate in gsp_predicates.items:
                    if not isinstance(gsp_predicate, GeneratorSelection | CombinedGeneratorSelection | SingleGeneratorSelection):
                        logger.debug(f"FAILED: gsp predicate is not a valid GeneratorSelection (got {gsp_predicate})")
                        return None

                    child_loops.append(Loop(gsp_predicate, body))

                return Loop(
                    SingleGeneratorSelection(generator, predicates),
                    ast_.Statements(child_loops),
                )
        return None


@dataclass
class RelationalSubtypingLoopSimplification(RewriteCollection):
    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.singleton_membership_in_predicate,
            self.total_membership_elimination,
            #             self.surjective_membership_elimination,
            self.concrete_domain_image,
            #             self.concrete_range_image,
            self.single_element_loop,
            #             self.singleton_membership_elimination,
        ]

    def single_element_loop(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case Loop(
                SingleGeneratorSelection(
                    ast_.In(
                        ast_.Identifier(_) as identifier,
                        ast_.Image(rel, elem),
                    ),
                    predicate,
                ),
                body,
            ) if ast_.SetType.is_relation(rel.get_type):
                if rel.get_type.relation_subtype is None:
                    logger.debug("FAILED: relation has no subtype information, cannot perform single element loop elimination")
                    return None

                if not rel.get_type.relation_subtype.many_to_one:
                    logger.debug("FAILED: relation is not many-to-one, cannot perform single element loop elimination")
                    return None

                return ast_.If(
                    predicate.find_and_replace(identifier, ast_.Call(rel, [elem])),
                    body.find_and_replace(identifier, ast_.Call(rel, [elem])),
                )
        return None

    def total_membership_elimination(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            # TODO make this more general, rn its too restricted to if statements created by concrete_domain_image
            # We want it to work for all non-generator predicates
            case ast_.If(
                ast_.In(
                    val,
                    ast_.Call(
                        ast_.Identifier("dom"),
                        [rel],
                    ),
                ),
                body,
            ) if ast_.SetType.is_relation(rel.get_type):

                if rel.get_type.relation_subtype is None:
                    logger.debug("FAILED: relation has no subtype information, cannot perform total membership elimination")
                    return None

                if not rel.get_type.relation_subtype.total:
                    logger.debug("FAILED: relation is not total, cannot perform total membership elimination")
                    return None

                # Really should be if True: body, but we can skip the boilerplate for now
                return body

        return None

    def concrete_domain_image(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case Loop(
                SingleGeneratorSelection(
                    ast_.In(
                        ast_.MapletIdentifier((left, right)),
                        rel,
                    ),
                    predicate,
                ),
                body,
            ) if ast_.SetType.is_relation(rel.get_type):

                substitution = None
                for predicate_item in predicate.items:
                    match predicate_item:
                        # Enumerations with one element will only have one element. Ideally we would use the type to look at the size of the relation/set
                        case ast_.Equal(l, val) if l == left and not val.contains_item(left):
                            substitution = (l, val)
                            break
                        case ast_.Equal(val, l) if l == left and not val.contains_item(left):
                            substitution = (l, val)
                            break

                if substitution is None:
                    logger.debug("FAILED: no suitable substitution found for concrete domain image optimization")
                    return None

                sub_left, val = substitution
                return ast_.If(
                    ast_.In(
                        val,
                        ast_.Call(
                            ast_.Identifier("dom"),
                            [rel],
                        ),
                    ),
                    Loop(
                        SingleGeneratorSelection(
                            ast_.In(right, ast_.Image(rel, val)),
                            ast_.And([predicate.find_and_replace(sub_left, val)]),
                        ),
                        body.find_and_replace(sub_left, val),
                    ),
                )

        return None

    def singleton_membership_in_predicate(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case Loop(
                SingleGeneratorSelection(
                    generator,
                    ast_.ListOp(predicates, ast_.ListOperator.AND),
                ),
                body,
            ):
                new_predicates: list[ast_.ASTNode] = []
                predicates_changed = False
                for predicate in predicates:
                    match predicate:
                        # Enumerations with one element will only have one element. Ideally we would use the type to look at the size of the relation/set
                        case ast_.In(ast_.Identifier(_) as identifier, ast_.Enumeration([value])):
                            # case ast_.In(_, rel) if ast_.SetType.is_singleton_set_type(rel.get_type):
                            predicates_changed = True
                            new_predicates.append(ast_.Equal(identifier, value))
                            continue
                        case _:
                            new_predicates.append(predicate)

                if not predicates_changed:
                    # We didn't actually match to any predicates of the form x in {y}
                    return None

                return Loop(
                    SingleGeneratorSelection(
                        generator,
                        ast_.And(new_predicates),
                    ),
                    body,
                )

        return None


#     def total_membership_elimination(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
#         match ast:
#             case Loop(
#                 SingleGeneratorSelection(_, ast_.ListOp(predicates, ast_.ListOperator.AND)),
#                 body,
#             ):
#                 new_predicates = []
#                 predicates_changed = False
#                 for predicate in predicates:
#                     match predicate:
#                         case ast_.In(_, rel) if ast_.SetType.is_total_relation(rel.get_type):
#                             predicates_changed = True
#                             continue
#                         case _:
#                             new_predicates.append(predicate)

#                 if predicates_changed:
#                     # We didn't actually match to any predicates of the form x in dom(R)
#                     return None

#                 if len(new_predicates) != len(predicates):
#                     return Loop(
#                         SingleGeneratorSelection(
#                             ast_.GeneratorSelection(
#                                 ast_.Identifier(""),  # Dummy identifier, won't be used
#                                 ast_.SetType.get_unit_set_type(),
#                             ),
#                             ast_.And(new_predicates),
#                         ),
#                         body,
#                     )

#         return None


# @dataclass
# class RelationalSubtypingLoopSimplification(RewriteCollection):
#     def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
#         return [
#             # self.total_membership_elimination,
#             # self.surjective_membership_elimination,
#             self.concrete_domain_image,
#             self.concrete_range_image,
#             self.single_element_elimination,
#             self.singleton_membership_elimination,
#         ]

#     def concrete_domain_image(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
#         match ast:
#             case Loop(
#                 SingleGeneratorSelection(
#                     ast_.In(ast_.MapletIdentifier(left, right), rel),
#                     ast_.And(predicates),
#                 ),
#                 body,
#             ) if ast_.SetType.is_relation(rel.get_type):
#                 concrete_domain_access = None
#                 for predicate in predicates:
#                     match predicate:
#                         case ast_.Equal(eq_to_left, const) if eq_to_left == left and not const.contains_item(left):
#                             concrete_domain_access = const

#         return None


@dataclass
class LoopsCodeGenerationCollection(RewriteCollection):

    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.conjunct_conditional,
        ]

    def conjunct_conditional(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case Loop(
                SingleGeneratorSelection(
                    generator,
                    predicates,
                ),
                body,
            ):
                if ast._env is None:
                    logger.debug(f"FAILED: no environment found in loop (cannot perform optimizations)")
                    return None

                free_predicates = []
                bound_predicates = []
                for predicate in predicates.items:
                    identifiers_within_predicate = predicate.find_all_instances(ast_.Identifier)

                    for identifier in identifiers_within_predicate:
                        # If the identifier is not bound outside of the quantifier or if it is used within the generator
                        if ast._env.get(identifier.name) is None or generator.contains_item(identifier):
                            bound_predicates.append(predicate)
                            break
                    else:
                        free_predicates.append(predicate)

                statement: ast_.ASTNode = body
                if bound_predicates:
                    statement = ast_.Statements(
                        [
                            ast_.If(
                                ast_.And(bound_predicates),
                                statement,
                            )
                        ]
                    )

                assert isinstance(generator.left, ast_.Identifier | ast_.MapletIdentifier), f"Generator should have an identifier on the left side (got {generator.left})"
                statement = ast_.For(
                    ast_.TupleIdentifier((generator.left,)),
                    generator.right,
                    statement,
                )

                if free_predicates:
                    statement = ast_.If(
                        ast_.And(free_predicates),
                        body=ast_.Statements([statement]),
                    )

                return ast_.Statements([statement])

        return None


@dataclass
class ReplaceAndSimplifyCollection(RewriteCollection):
    bound_generator_variables: set[ast_.Identifier] = field(default_factory=set)

    def apply_all_rules_one_traversal(self, ast):
        # Before entering a new quantifier, record currently bound variables
        # (so we can restore them later)
        bound_generator_variables_before = deepcopy(self.bound_generator_variables)
        if isinstance(ast, ast_.For):
            logger.debug(f"For loop found with bound variables: {ast.iterable_names.flatten()}")
            # Add newly accessible (bound) loop variables, used for equality elimination
            self.bound_generator_variables |= ast.iterable_names.flatten()

        ast = super().apply_all_rules_one_traversal(ast)
        logger.debug(f"AST after applying all rules: {ast.pretty_print_algorithmic()}")

        # Restore bound variable record since we have exited the possibly nested quantifier
        self.bound_generator_variables = bound_generator_variables_before

        return ast

    def _rewrite_collection(self) -> list[Callable[[ast_.ASTNode], ast_.ASTNode | None]]:
        return [
            self.equality_elimination,
            self.remove_empty_not,
            self.if_true,
            self.simplify_equalities,
            self.simplify_and,
            self.simplify_or,
            self.flatten_nested_statements,
        ]

    def if_true(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.If(ast_.True_(), body):
                return body
        return None

    def remove_empty_not(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.UnaryOp(
                ast_.ListOp([], ast_.ListOperator.OR),
                ast_.UnaryOperator.NOT,
            ):
                return ast_.True_()
            case ast_.UnaryOp(
                ast_.ListOp([], ast_.ListOperator.AND),
                ast_.UnaryOperator.NOT,
            ):
                return ast_.True_()
        return None

    def equality_elimination(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.If(
                ast_.ListOp(elems, ast_.ListOperator.AND) as predicate,
                body,
            ):
                if ast._env is None:
                    logger.debug(f"FAILED: no environment found in if (cannot perform optimizations)")
                    return None

                new_predicate_items = predicate.items
                substitution = None
                for and_clause in elems:
                    if not isinstance(and_clause, ast_.BinaryOp) or and_clause.op_type != ast_.BinaryOperator.EQUAL:
                        continue

                    if isinstance(and_clause.left, ast_.Identifier) and and_clause.left not in self.bound_generator_variables and ast._env.get(and_clause.left.name) is None:
                        substitution = and_clause
                        new_predicate_items.remove(and_clause)
                        break
                    if isinstance(and_clause.right, ast_.Identifier) and and_clause.right not in self.bound_generator_variables and ast._env.get(and_clause.right.name) is None:
                        substitution = ast_.Equal(
                            and_clause.right,
                            and_clause.left,
                        )
                        new_predicate_items.remove(and_clause)
                        break

                if not substitution:
                    logger.debug(f"FAILED: no substitutions found in OR quantifier (current environment is {ast._env}), free variables are {ast.free}")
                    return None
                logger.debug(f"Running substitution {substitution} in {elems}")

                new_predicate = ast_.And(new_predicate_items)
                new_predicate.find_and_replace(
                    substitution.left,
                    substitution.right,
                )
                body.find_and_replace(
                    substitution.left,
                    substitution.right,
                )
                return ast_.If(
                    new_predicate,
                    body,
                )

        return None

    def simplify_equalities(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.BinaryOp(x, y, ast_.BinaryOperator.EQUAL):
                if x == y:
                    return ast_.True_()
        return None

    def simplify_and(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.ListOp([], ast_.ListOperator.AND):
                return ast_.True_()
            case ast_.ListOp(elems, ast_.ListOperator.AND):
                new_elems = []
                for elem in elems:
                    if isinstance(elem, ast_.True_):
                        continue
                    if isinstance(elem, ast_.False_):
                        return ast_.False_()
                    new_elems.append(elem)

                if elems == new_elems:
                    logger.debug("FAILED: no simplification applied to AND list operation (no clauses were removed)")
                    return None

                if not new_elems:
                    return ast_.And([])

                return ast_.And(new_elems)
        return None

    def simplify_or(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.ListOp([], ast_.ListOperator.OR):
                return ast_.True_()
            case ast_.ListOp(elems, ast_.ListOperator.OR):
                new_elems = []
                for elem in elems:
                    if isinstance(elem, ast_.True_):
                        return ast_.True_()
                    if isinstance(elem, ast_.False_):
                        continue
                    new_elems.append(elem)

                if elems == new_elems:
                    logger.debug("FAILED: no simplification applied to OR list operation (no clauses were removed)")
                    return None

                if not new_elems:
                    return ast_.Or([])

                return ast_.Or(new_elems)
        return None

    def flatten_nested_statements(self, ast: ast_.ASTNode) -> ast_.ASTNode | None:
        match ast:
            case ast_.Statements(items):

                if not any(map(lambda x: isinstance(x, ast_.Statements), items)):
                    return None

                new_statements: list[ast_.ASTNode] = []
                for item in items:
                    if not isinstance(item, ast_.Statements):
                        new_statements.append(item)
                        continue

                    new_statements.extend(item.items)

                return ast_.Statements(new_statements)
        return None


REWRITE_COLLECTION: list[type[RewriteCollection]] = [
    SyntacticSugarForBags,
    SyntacticSugarForSequences,
    ComprehensionConstructionCollection,
    BuiltinFunctions,
    ComprehensionConstructionCollection,
    DisjunctiveNormalFormCollection,
    OrWrappingCollection,
    GeneratorSelectionCollection,
    GSPToLoopsCollection,
    # RelationalSubtypingLoopSimplification,
    LoopsCodeGenerationCollection,
    ReplaceAndSimplifyCollection,
]
