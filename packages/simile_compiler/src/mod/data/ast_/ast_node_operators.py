from __future__ import annotations
from enum import Enum, auto
from typing import TypeGuard, Literal


class BinaryOperator(Enum):
    """All binary operators in Simile (except for relation type operators)."""

    # Bools
    IMPLIES = auto()
    EQUIVALENT = auto()
    NOT_EQUIVALENT = auto()
    # Numbers
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    INT_DIVIDE = auto()
    MODULO = auto()
    EXPONENT = auto()
    # Num-to-bool operators
    LESS_THAN = auto()
    LESS_THAN_OR_EQUAL = auto()
    GREATER_THAN = auto()
    GREATER_THAN_OR_EQUAL = auto()
    # Equality
    EQUAL = auto()
    NOT_EQUAL = auto()
    IS = auto()
    IS_NOT = auto()
    # Set operators
    IN = auto()
    NOT_IN = auto()
    UNION = auto()
    INTERSECTION = auto()
    DIFFERENCE = auto()
    # Set-to-bool operators
    SUBSET = auto()
    SUBSET_EQ = auto()
    SUPERSET = auto()
    SUPERSET_EQ = auto()
    NOT_SUBSET = auto()
    NOT_SUBSET_EQ = auto()
    NOT_SUPERSET = auto()
    NOT_SUPERSET_EQ = auto()
    # Relation operators
    MAPLET = auto()
    RELATION_OVERRIDING = auto()
    COMPOSITION = auto()
    CARTESIAN_PRODUCT = auto()
    UPTO = auto()
    # Relation/Set operations
    DOMAIN_SUBTRACTION = auto()
    DOMAIN_RESTRICTION = auto()
    RANGE_SUBTRACTION = auto()
    RANGE_RESTRICTION = auto()
    CONCAT = auto()

    def pretty_print(self) -> str:
        pretty_print_lookup = {
            BinaryOperator.IMPLIES: "⇒",
            BinaryOperator.EQUIVALENT: "≡",
            BinaryOperator.NOT_EQUIVALENT: "≢",
            #: ,
            BinaryOperator.ADD: "+",
            BinaryOperator.SUBTRACT: "-",
            BinaryOperator.MULTIPLY: "*",
            BinaryOperator.DIVIDE: "/",
            BinaryOperator.INT_DIVIDE: "div",
            BinaryOperator.MODULO: "mod",
            BinaryOperator.EXPONENT: "^",
            #: ,
            BinaryOperator.LESS_THAN: "<",
            BinaryOperator.LESS_THAN_OR_EQUAL: "≤",
            BinaryOperator.GREATER_THAN: ">",
            BinaryOperator.GREATER_THAN_OR_EQUAL: "≥",
            #: ,
            BinaryOperator.EQUAL: "=",
            BinaryOperator.NOT_EQUAL: "≠",
            BinaryOperator.IS: "is",
            BinaryOperator.IS_NOT: "is not",
            #: ,
            BinaryOperator.IN: "∈",
            BinaryOperator.NOT_IN: "∉",
            BinaryOperator.UNION: "∪",
            BinaryOperator.INTERSECTION: "∩",
            BinaryOperator.DIFFERENCE: "∖",
            #: ,
            BinaryOperator.SUBSET: "⊂",
            BinaryOperator.SUBSET_EQ: "⊆",
            BinaryOperator.SUPERSET: "⊃",
            BinaryOperator.SUPERSET_EQ: "⊇",
            BinaryOperator.NOT_SUBSET: "⊄",
            BinaryOperator.NOT_SUBSET_EQ: "⊈",
            BinaryOperator.NOT_SUPERSET: "⊅",
            BinaryOperator.NOT_SUPERSET_EQ: "⊉",
            #: ,
            BinaryOperator.MAPLET: "↦",
            BinaryOperator.RELATION_OVERRIDING: "⊕",
            BinaryOperator.COMPOSITION: "∘",
            BinaryOperator.CARTESIAN_PRODUCT: "×",
            BinaryOperator.UPTO: "..",
            #: ,
            BinaryOperator.DOMAIN_SUBTRACTION: "◁",
            BinaryOperator.DOMAIN_RESTRICTION: "⩤",
            BinaryOperator.RANGE_SUBTRACTION: "▷",
            BinaryOperator.RANGE_RESTRICTION: "⩥",
            #: ,
            BinaryOperator.CONCAT: "⧺",
        }
        return pretty_print_lookup.get(self, self.name)


class RelationOperator(Enum):
    """All relation type binary operators in Simile."""

    RELATION = auto()
    TOTAL_RELATION = auto()
    SURJECTIVE_RELATION = auto()
    TOTAL_SURJECTIVE_RELATION = auto()
    PARTIAL_FUNCTION = auto()
    TOTAL_FUNCTION = auto()
    PARTIAL_INJECTION = auto()
    TOTAL_INJECTION = auto()
    PARTIAL_SURJECTION = auto()
    TOTAL_SURJECTION = auto()
    BIJECTION = auto()

    def pretty_print(self) -> str:
        pretty_print_lookup = {
            RelationOperator.RELATION: "↔",
            RelationOperator.TOTAL_RELATION: "<<->",
            RelationOperator.SURJECTIVE_RELATION: "<->>",
            RelationOperator.TOTAL_SURJECTIVE_RELATION: "<<->>",
            RelationOperator.PARTIAL_FUNCTION: "⇸",
            RelationOperator.TOTAL_FUNCTION: "→",
            RelationOperator.PARTIAL_INJECTION: "⤔",
            RelationOperator.TOTAL_INJECTION: "↣",
            RelationOperator.PARTIAL_SURJECTION: "⤀",
            RelationOperator.TOTAL_SURJECTION: "↠",
            RelationOperator.BIJECTION: "⤖",
        }
        return pretty_print_lookup.get(self, self.name)


class UnaryOperator(Enum):
    """All unary operators in Simile."""

    NOT = auto()
    NEGATIVE = auto()
    POWERSET = auto()
    NONEMPTY_POWERSET = auto()
    INVERSE = auto()

    def pretty_print(self) -> str:
        pretty_print_lookup = {
            UnaryOperator.NOT: "¬",
            UnaryOperator.NEGATIVE: "-",
            UnaryOperator.POWERSET: "ℙ",
            UnaryOperator.NONEMPTY_POWERSET: "ℙ₁",
            UnaryOperator.INVERSE: "⁻¹",
        }
        return pretty_print_lookup.get(self, self.name)


class ListOperator(Enum):
    """And/Or operators"""

    AND = auto()
    OR = auto()

    def pretty_print(self) -> str:
        pretty_print_lookup = {
            ListOperator.AND: "∧",
            ListOperator.OR: "∨",
        }
        return pretty_print_lookup.get(self, self.name)


class QuantifierOperator(Enum):
    FORALL = auto()
    EXISTS = auto()

    UNION_ALL = auto()
    INTERSECTION_ALL = auto()

    SUM = auto()
    PRODUCT = auto()

    SEQUENCE = auto()
    SET = auto()
    RELATION = auto()
    BAG = auto()

    def is_bool_quantifier(self) -> bool:
        """Check if the quantifier operator is a boolean quantifier (FORALL or EXISTS)."""
        return self in {QuantifierOperator.FORALL, QuantifierOperator.EXISTS}

    def is_collection_operator(self) -> bool:
        """Check if the quantifier operator is a collection operator (SEQUENCE, SET, RELATION, BAG)."""
        return self in {
            QuantifierOperator.SEQUENCE,
            QuantifierOperator.SET,
            QuantifierOperator.RELATION,
            QuantifierOperator.BAG,
        }

    def is_numerical_quantifier(self) -> bool:
        """Check if the quantifier operator is a numerical quantifier (SUM or PRODUCT)."""
        return self in {QuantifierOperator.SUM, QuantifierOperator.PRODUCT}

    def is_general_collection_operator(self) -> bool:
        """Check if the quantifier operator is a general collection operator (UNION_ALL or INTERSECTION_ALL)."""
        return self in {
            QuantifierOperator.UNION_ALL,
            QuantifierOperator.INTERSECTION_ALL,
        }

    @classmethod
    def from_collection_operator(cls, other: CollectionOperator) -> QuantifierOperator | None:
        match other:
            case CollectionOperator.SEQUENCE:
                return QuantifierOperator.SEQUENCE
            case CollectionOperator.SET:
                return QuantifierOperator.SET
            case CollectionOperator.RELATION:
                return QuantifierOperator.RELATION
            case CollectionOperator.BAG:
                return QuantifierOperator.BAG
            case _:
                return None

    def pretty_print(self) -> str:
        pretty_print_lookup = {
            QuantifierOperator.FORALL: "∀",
            QuantifierOperator.EXISTS: "∃",
            QuantifierOperator.UNION_ALL: "⋃",
            QuantifierOperator.INTERSECTION_ALL: "⋂",
            QuantifierOperator.SUM: "Σ",
            QuantifierOperator.PRODUCT: "Π",
            QuantifierOperator.SEQUENCE: "⟨⟩",
            QuantifierOperator.SET: "{}",
            QuantifierOperator.RELATION: "{}",
            QuantifierOperator.BAG: "⟦⟧",
        }
        return pretty_print_lookup.get(self, self.name)


class ControlFlowOperator(Enum):
    """Control flow operators in Simile."""

    BREAK = auto()
    CONTINUE = auto()
    SKIP = auto()

    def pretty_print(self) -> str:
        pretty_print_lookup = {
            ControlFlowOperator.BREAK: "break",
            ControlFlowOperator.CONTINUE: "continue",
            ControlFlowOperator.SKIP: "skip",
        }
        return pretty_print_lookup.get(self, self.name)


class CollectionOperator(Enum):
    """Collection operators in Simile."""

    SEQUENCE = auto()
    SET = auto()
    RELATION = auto()
    BAG = auto()
    TUPLE = auto()

    def pretty_print(self) -> str:
        quantifier_op_version = QuantifierOperator.from_collection_operator(self)
        return quantifier_op_version.pretty_print() if quantifier_op_version else self.name


Operators = BinaryOperator | RelationOperator | UnaryOperator | ListOperator | QuantifierOperator | ControlFlowOperator
"""Type alias for all operator enums in Simile."""
