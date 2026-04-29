# This file is auto-generated through packages\simile_compiler\src\mod\ast_\ast_nodes_generated.py. Do not edit manually.
from dataclasses import dataclass, field

from src.mod.data.ast_.operators import (
    BinaryOperator,
    RelationOperator,
    UnaryOperator,
    ListOperator,
    QuantifierOperator,
    ControlFlowOperator,
    CollectionOperator,
    Operators,
)
from src.mod.data.ast_.common import (
    True_,
    BinaryOp,
    RelationOp,
    ListOp,
    UnaryOp,
    Quantifier,
    QualifiedQuantifier,
    ControlFlowStmt,
    Enumeration,
)
from src.mod.data.ast_.base import ASTNode


@dataclass
class Implies(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.IMPLIES


@dataclass
class Equivalent(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.EQUIVALENT


@dataclass
class NotEquivalent(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_EQUIVALENT


@dataclass
class Add(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.ADD


@dataclass
class Subtract(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.SUBTRACT


@dataclass
class Multiply(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.MULTIPLY


@dataclass
class Divide(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.DIVIDE


@dataclass
class Modulo(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.MODULO


@dataclass
class Exponent(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.EXPONENT


@dataclass
class LessThan(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.LESS_THAN


@dataclass
class LessThanOrEqual(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.LESS_THAN_OR_EQUAL


@dataclass
class GreaterThan(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.GREATER_THAN


@dataclass
class GreaterThanOrEqual(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.GREATER_THAN_OR_EQUAL


@dataclass
class Equal(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.EQUAL


@dataclass
class NotEqual(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_EQUAL


@dataclass
class Is(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.IS


@dataclass
class IsNot(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.IS_NOT


@dataclass
class In(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.IN


@dataclass
class NotIn(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_IN


@dataclass
class Union(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.UNION


@dataclass
class Intersection(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.INTERSECTION


@dataclass
class Difference(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.DIFFERENCE


@dataclass
class Subset(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.SUBSET


@dataclass
class SubsetEq(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.SUBSET_EQ


@dataclass
class Superset(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.SUPERSET


@dataclass
class SupersetEq(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.SUPERSET_EQ


@dataclass
class NotSubset(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_SUBSET


@dataclass
class NotSubsetEq(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_SUBSET_EQ


@dataclass
class NotSuperset(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_SUPERSET


@dataclass
class NotSupersetEq(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.NOT_SUPERSET_EQ


@dataclass
class Maplet(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.MAPLET


@dataclass
class RelationOverriding(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.RELATION_OVERRIDING


@dataclass
class Composition(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.COMPOSITION


@dataclass
class CartesianProduct(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.CARTESIAN_PRODUCT


@dataclass
class Upto(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.UPTO


@dataclass
class DomainSubtraction(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.DOMAIN_SUBTRACTION


@dataclass
class DomainRestriction(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.DOMAIN_RESTRICTION


@dataclass
class RangeSubtraction(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.RANGE_SUBTRACTION


@dataclass
class RangeRestriction(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.RANGE_RESTRICTION


@dataclass
class Concat(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.CONCAT


@dataclass
class IntDivide(BinaryOp):
    op_type: BinaryOperator = BinaryOperator.INT_DIVIDE


@dataclass
class Relation(RelationOp):
    op_type: RelationOperator = RelationOperator.RELATION


@dataclass
class TotalRelation(RelationOp):
    op_type: RelationOperator = RelationOperator.TOTAL_RELATION


@dataclass
class SurjectiveRelation(RelationOp):
    op_type: RelationOperator = RelationOperator.SURJECTIVE_RELATION


@dataclass
class TotalSurjectiveRelation(RelationOp):
    op_type: RelationOperator = RelationOperator.TOTAL_SURJECTIVE_RELATION


@dataclass
class PartialFunction(RelationOp):
    op_type: RelationOperator = RelationOperator.PARTIAL_FUNCTION


@dataclass
class TotalFunction(RelationOp):
    op_type: RelationOperator = RelationOperator.TOTAL_FUNCTION


@dataclass
class PartialInjection(RelationOp):
    op_type: RelationOperator = RelationOperator.PARTIAL_INJECTION


@dataclass
class TotalInjection(RelationOp):
    op_type: RelationOperator = RelationOperator.TOTAL_INJECTION


@dataclass
class PartialSurjection(RelationOp):
    op_type: RelationOperator = RelationOperator.PARTIAL_SURJECTION


@dataclass
class TotalSurjection(RelationOp):
    op_type: RelationOperator = RelationOperator.TOTAL_SURJECTION


@dataclass
class Bijection(RelationOp):
    op_type: RelationOperator = RelationOperator.BIJECTION


@dataclass
class And(ListOp):
    op_type: ListOperator = ListOperator.AND


@dataclass
class Or(ListOp):
    op_type: ListOperator = ListOperator.OR


@dataclass
class Not(UnaryOp):
    op_type: UnaryOperator = UnaryOperator.NOT


@dataclass
class Negative(UnaryOp):
    op_type: UnaryOperator = UnaryOperator.NEGATIVE


@dataclass
class Powerset(UnaryOp):
    op_type: UnaryOperator = UnaryOperator.POWERSET


@dataclass
class NonemptyPowerset(UnaryOp):
    op_type: UnaryOperator = UnaryOperator.NONEMPTY_POWERSET


@dataclass
class Inverse(UnaryOp):
    op_type: UnaryOperator = UnaryOperator.INVERSE


@dataclass
class Break(ControlFlowStmt):
    op_type: ControlFlowOperator = ControlFlowOperator.BREAK


@dataclass
class Continue(ControlFlowStmt):
    op_type: ControlFlowOperator = ControlFlowOperator.CONTINUE


@dataclass
class Skip(ControlFlowStmt):
    op_type: ControlFlowOperator = ControlFlowOperator.SKIP


@dataclass
class UnionAll(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.UNION_ALL


@dataclass
class IntersectionAll(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.INTERSECTION_ALL


@dataclass
class Sum(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.SUM


@dataclass
class Product(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.PRODUCT


@dataclass
class SequenceComprehension(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.SEQUENCE


@dataclass
class SetComprehension(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.SET


@dataclass
class RelationComprehension(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.RELATION


@dataclass
class BagComprehension(Quantifier):
    op_type: QuantifierOperator = QuantifierOperator.BAG


@dataclass
class QualifiedUnionAll(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.UNION_ALL


@dataclass
class QualifiedIntersectionAll(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.INTERSECTION_ALL


@dataclass
class QualifiedSum(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.SUM


@dataclass
class QualifiedProduct(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.PRODUCT


@dataclass
class QualifiedSequenceComprehension(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.SEQUENCE


@dataclass
class QualifiedSetComprehension(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.SET


@dataclass
class QualifiedRelationComprehension(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.RELATION


@dataclass
class QualifiedBagComprehension(QualifiedQuantifier):
    op_type: QuantifierOperator = QuantifierOperator.BAG


@dataclass
class SequenceEnumeration(Enumeration):
    op_type: CollectionOperator = CollectionOperator.SEQUENCE


@dataclass
class SetEnumeration(Enumeration):
    op_type: CollectionOperator = CollectionOperator.SET


@dataclass
class RelationEnumeration(Enumeration):
    op_type: CollectionOperator = CollectionOperator.RELATION


@dataclass
class BagEnumeration(Enumeration):
    op_type: CollectionOperator = CollectionOperator.BAG


@dataclass
class Forall(Quantifier):
    expression: ASTNode = field(default_factory=True_)
    op_type: QuantifierOperator = QuantifierOperator.FORALL


@dataclass
class Exists(Quantifier):
    expression: ASTNode = field(default_factory=True_)
    op_type: QuantifierOperator = QuantifierOperator.EXISTS


@dataclass
class QualifiedForall(QualifiedQuantifier):
    expression: ASTNode = field(default_factory=True_)
    op_type: QuantifierOperator = QuantifierOperator.FORALL


@dataclass
class QualifiedExists(QualifiedQuantifier):
    expression: ASTNode = field(default_factory=True_)
    op_type: QuantifierOperator = QuantifierOperator.EXISTS
