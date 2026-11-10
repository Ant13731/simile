from __future__ import annotations
from dataclasses import dataclass, field, Field, fields, is_dataclass
from typing import Callable, ClassVar, Any, Self, Container, TYPE_CHECKING, TypeVar, Generic, Sequence, TypeAlias, overload
from warnings import deprecated
from pathlib import Path


from src.mod.data.helpers.dataclass import flatten
from src.mod.data.ast_.base import ASTNode
from src.mod.data.ast_.pre_symbol_table import (
    Identifier,
    MapletIdentifier,
    TupleIdentifier,
)
from src.mod.data.ast_.post_symbol_table import (
    Symbol,
    MapletSymbol,
    TupleSymbol,
    SymbolListTypes,
    RecordDefSymbol,
    ProcedureDefSymbol,
)
from src.mod.data.ast_.operators import (
    BinaryOperator,
    RelationOperator,
    UnaryOperator,
    ListOperator,
    QuantifierOperator,
    ControlFlowOperator,
    CollectionOperator,
    ImportOperator,
    Operators,
)

from src.mod.data.symbol_table.entry import ScopeTableEntry

if TYPE_CHECKING:
    from src.mod.data.types.base import BaseType


# TODO generate constructors for the typed dataclasses as a sort of shorthand, especially useful for matching/TRS rule creation
# Generate them from enums directly - ex. print(type_writer(op.name.capitalize() for op in BinaryOperator))
@dataclass
class Int(ASTNode):
    value: str


@dataclass
class Float(ASTNode):
    value: str


@dataclass
class String(ASTNode):
    value: str


@dataclass
class True_(ASTNode):
    pass


@dataclass
class False_(ASTNode):
    pass


@dataclass
class None_(ASTNode):
    pass


class InheritedEqMixin:
    """Introduces structural equality between super/subclasses that ignore type names.

    Only needs to be mixed in the parent class. Must be used with dataclasses."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False

        assert is_dataclass(self), "InheritedEqMixin can only be used with dataclasses"

        if not is_dataclass(other):
            return False

        if len(fields(self)) != len(fields(other)):
            return False

        for f in fields(self):
            if f.name.startswith("_"):
                continue
            self_value = getattr(self, f.name)
            try:
                other_value = getattr(other, f.name)
            except AttributeError:
                return False
            if self_value != other_value:
                return False
        return True


@dataclass(eq=False)
class BinaryOp(InheritedEqMixin, ASTNode):
    left: ASTNode
    right: ASTNode
    op_type: BinaryOperator

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        for f in fields(self):
            if f.name.startswith("_"):
                continue
            self_value = getattr(self, f.name)
            try:
                other_value = getattr(other, f.name)
            except AttributeError:
                return False
            if self_value != other_value:
                return False
        return True

    @property
    def bound(self) -> set[Identifier]:
        return self.left.bound | self.right.bound

    @property
    def free(self) -> set[Identifier]:
        return self.left.free | self.right.free

    def well_formed(self) -> bool:
        return all(
            [
                self.left.well_formed(),
                self.right.well_formed(),
                self.left.free & self.right.bound == set(),
                self.left.bound & self.right.free == set(),
                self.left.bound & self.right.bound == set(),
            ]
        )

    def temporary_freeze_hash(self) -> int:
        return hash((self.left, self.right, self.op_type))


@dataclass(eq=False)
class RelationOp(InheritedEqMixin, ASTNode):
    left: ASTNode
    right: ASTNode
    op_type: RelationOperator

    @property
    def bound(self) -> set[Identifier]:
        return self.left.bound | self.right.bound

    @property
    def free(self) -> set[Identifier]:
        return self.left.free | self.right.free

    def well_formed(self) -> bool:
        return all(
            [
                self.left.well_formed(),
                self.right.well_formed(),
                self.left.free.isdisjoint(self.right.bound),
                self.left.bound.isdisjoint(self.right.free),
                self.left.bound.isdisjoint(self.right.bound),
            ]
        )


@dataclass(eq=False)
class UnaryOp(InheritedEqMixin, ASTNode):
    value: ASTNode
    op_type: UnaryOperator


@dataclass(eq=False)
class ListOp(InheritedEqMixin, ASTNode):
    items: list[ASTNode]
    op_type: ListOperator

    def __post_init__(self) -> None:
        super().__post_init__()

        # Flatten nested ListOps of the same type (eg. nested Ands flatten to one list)
        flattened_objs = []
        for obj in self.items:
            if isinstance(obj, ListOp) and obj.op_type == self.op_type:
                flattened_objs += obj.items
            else:
                flattened_objs.append(obj)
        self.items = flattened_objs

    @property
    def bound(self) -> set[Identifier]:
        return set().union(*(item.bound for item in self.items))

    @property
    def free(self) -> set[Identifier]:
        return set().union(*(item.free for item in self.items))

    def well_formed(self) -> bool:
        if not all(item.well_formed() for item in self.items):
            return False
        for item in self.items:
            for other in self.items:
                if item == other:
                    continue
                if not item.free.isdisjoint(other.bound):
                    return False
                if not item.bound.isdisjoint(other.free):
                    return False
                if not item.bound.isdisjoint(other.bound):
                    return False
        return True


# TODO move to parser_only file (once typing/semantic analysis is sorted out)
@deprecated("use v3")
@dataclass(eq=False)
class Quantifier(ASTNode):
    predicate: ListOp  # includes generators
    expression: ASTNode
    op_type: QuantifierOperator
    # demoted_predicate: ListOp | None = None  # guaranteed to NOT include generators - should only be filled in with an AND

    def __post_init__(self) -> None:
        super().__post_init__()

        # After semantic analysis, all Quantifiers should have at least one bound identifier + generator suitable to loop over
        # Relations use MapletIdentifiers, sets use regular identifiers. At the end of optimization,
        # one quantifier will only bind one new identifier and translate down to (at most) one for-loop
        #
        # One identifier name should appear only once in the set of bound identifiers
        self._bound_identifiers: set[Identifier | MapletIdentifier] = set()  # | None = None
        self._temp_bound_identifiers_before_qualified_promotion: TupleIdentifier | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False

        if len(fields(self)) != len(fields(other)):
            return False

        for f in fields(self):
            if f.name not in map(lambda x: x.name, fields(other)):
                return False

        if self.op_type != other.op_type:
            return False
        if self.all_predicates != other.all_predicates:
            return False
        if self.expression != other.expression:
            return False

        for f in fields(self):
            if f.name.startswith("_"):
                continue
            self_value = getattr(self, f.name)
            try:
                other_value = getattr(other, f.name)
            except AttributeError:
                return False
            if self_value != other_value:
                return False
        return True

    @property
    def all_predicates(self) -> ASTNode:
        """Get all predicates in the quantifier, including demoted predicates."""
        predicates = self.predicate
        # if self.demoted_predicate:
        # predicates = ListOp.flatten_and_join([self.predicate, self.demoted_predicate], ListOperator.AND)
        return predicates

    @property
    def bound(self) -> set[Identifier]:
        if self._bound_identifiers:
            return self.all_predicates.bound | self.expression.bound | self.flatten_bound_identifiers()
        return self.all_predicates.bound | self.expression.bound | self.expression.free

    @property
    def free(self) -> set[Identifier]:
        if self._bound_identifiers:
            return (self.all_predicates.free | self.expression.free) - self.flatten_bound_identifiers()
        return self.all_predicates.free - self.expression.free

    def well_formed(self) -> bool:
        check_list = [
            self.all_predicates.well_formed(),
            self.expression.well_formed(),
            self.all_predicates.bound.isdisjoint(self.expression.bound),
            self.all_predicates.bound.isdisjoint(self.expression.free),
        ]

        if self._bound_identifiers:
            check_list += [TupleIdentifier(tuple(self._bound_identifiers)).well_formed()]

        if self._bound_identifiers:
            check_list += [
                self.all_predicates.free.isdisjoint(self.expression.bound),
                self.all_predicates.bound.isdisjoint(self._bound_identifiers),
                self.expression.bound.isdisjoint(self._bound_identifiers),
            ]

        return all(check_list)

    def flatten_bound_identifiers(self) -> set[Identifier]:
        identifiers = set()
        for i in self._bound_identifiers:
            identifiers |= i.flatten()
        return identifiers


@deprecated("use v3")
@dataclass(eq=False)
class QualifiedQuantifier(ASTNode):
    bound_identifiers: TupleIdentifier | TupleSymbol
    predicate: ListOp  # includes generators
    expression: ASTNode
    op_type: QuantifierOperator

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False

        if len(fields(self)) != len(fields(other)):
            return False

        for f in fields(self):
            if f.name not in map(lambda x: x.name, fields(other)):
                return False

        if self.op_type != other.op_type:
            return False
        if self.predicate != other.predicate:
            return False
        if self.expression != other.expression:
            return False
        if self.bound_identifiers != other.bound_identifiers:
            return False

        for f in fields(self):
            if f.name.startswith("_"):
                continue
            self_value = getattr(self, f.name)
            try:
                other_value = getattr(other, f.name)
            except AttributeError:
                return False
            if self_value != other_value:
                return False
        return True


@dataclass(eq=False)
class Quantifier3(ASTNode):
    body: QuantifierBody
    op_type: QuantifierOperator


# TODO make an identifier and a symbol version?
@dataclass
class Generator(ASTNode):
    identifiers: TupleIdentifier | Identifier | TupleSymbol | Symbol
    set_: ASTNode
    predicate: ASTNode | True_


@dataclass
class QuantifierBody(ASTNode):
    generators: list[Generator]
    end_or_branch: ASTNode | list[QuantifierBody]


@dataclass
class Fold(ASTNode):
    accumulator_init: Assignment
    quantifier_body: QuantifierBody


@dataclass
class IterGenerator(ASTNode):
    generator: Generator
    assignments: list[Assignment]


@dataclass
class IterBodyEnd(ASTNode):
    body: ASTNode
    return_value: TupleIdentifier | Identifier | TupleSymbol | Symbol


@dataclass
class IterBody(ASTNode):
    generators: list[IterGenerator]
    end_or_branch: IterBodyEnd | list[IterBody]


@dataclass
class Iter(ASTNode):
    body: IterBody


@dataclass(eq=False)
class Enumeration(InheritedEqMixin, ASTNode):
    items: list[ASTNode]
    op_type: CollectionOperator

    @property
    def bound(self) -> set[Identifier]:
        return set().union(*(item.bound for item in self.items))

    @property
    def free(self) -> set[Identifier]:
        return set().union(*(item.free for item in self.items))

    def well_formed(self) -> bool:
        if not all(item.well_formed() for item in self.items):
            return False
        for i in range(len(self.items)):
            for j in range(len(self.items)):
                if i == j:
                    continue
                # Is this too restrictive? this would block statements like {{x | x > 0}, {x | x > 0}}
                # which may be perfectly valid if x is only locally bound...
                if not self.items[i].bound.isdisjoint(self.items[j].bound):
                    return False
                if not self.items[i].bound.isdisjoint(self.items[j].free):
                    return False
        return True


@dataclass
class Type_(ASTNode):
    type_: ASTNode
    generics: list[ASTNode] = field(default_factory=list)

    @property
    def free(self) -> set[Identifier]:
        return self.type_.free

    @property
    def bound(self) -> set[Identifier]:
        return self.type_.bound

    def well_formed(self) -> bool:
        return self.type_.well_formed()


@dataclass
class LambdaDef(ASTNode):
    params: TupleIdentifier | TupleSymbol
    predicate: ASTNode
    expression: ASTNode

    @property
    def bound(self) -> set[Identifier]:
        return set(self.params.free) | self.predicate.bound | self.expression.bound

    @property
    def free(self) -> set[Identifier]:
        return (self.predicate.free | self.expression.free) - set(self.params.free)

    def well_formed(self) -> bool:
        return all(
            [
                all(param.well_formed() for param in self.params.free),
                self.predicate.well_formed(),
                self.expression.well_formed(),
                self.predicate.bound.isdisjoint(self.expression.free),
                self.expression.bound.isdisjoint(self.predicate.free),
                self.predicate.bound.isdisjoint(self.expression.bound),
                self.predicate.bound.isdisjoint(set(self.params.free)),
                self.expression.bound.isdisjoint(set(self.params.free)),
            ]
        )


@dataclass
class RecordAccess(ASTNode):
    record: ASTNode
    field_name: Identifier


@dataclass
class Call(ASTNode):
    target: ASTNode
    args: list[ASTNode]


@dataclass
class Image(ASTNode):
    target: ASTNode
    indices: list[ASTNode]


@dataclass
class TypedName(ASTNode):
    name: Identifier | ASTNode
    type_: Type_ | None_


@dataclass
class Assignment(ASTNode):
    target: ASTNode
    value: ASTNode
    choice_assignment: bool


@dataclass
class TraitApplication(ASTNode):
    target: ASTNode
    traits: list[ASTNode]


@dataclass
class Return(ASTNode):
    value: ASTNode | None_


@dataclass(eq=False)
class ControlFlowStmt(InheritedEqMixin, ASTNode):
    op_type: ControlFlowOperator


@dataclass
class Statements(ASTNode):
    items: list[ASTNode]


@dataclass
class Else(ASTNode):
    body: ASTNode | Statements


@dataclass
class If(ASTNode):
    condition: ASTNode
    body: ASTNode | Statements
    else_body: ElseIf | Else | None_ = field(default_factory=None_)


@dataclass
class ElseIf(ASTNode):
    condition: ASTNode
    body: ASTNode | Statements
    else_body: ElseIf | Else | None_ = field(default_factory=None_)


@dataclass
class For(ASTNode):
    iterable_names: TupleIdentifier | TupleSymbol | Identifier | Symbol
    iterable: ASTNode
    body: ASTNode | Statements

    @property
    def bound(self) -> set[Identifier]:
        return self.iterable_names.free


@dataclass
class While(ASTNode):
    condition: ASTNode
    body: ASTNode | Statements


@dataclass
class TupleLiteral(ASTNode):
    items: list[ASTNode]


@dataclass
class Import(ASTNode):
    module_file_path: Path
    import_objects: list[str]
    operator: ImportOperator


@dataclass
class Start(ASTNode):
    body: Statements | None_
    original_text: str = field(compare=False)


Primitive = Int | Float | String | True_ | False_ | None_
Collection = Enumeration | TupleLiteral | Quantifier3
Primary = RecordAccess | Call | Image | Collection | Primitive | Identifier
Predicate = BinaryOp | UnaryOp | ListOp | Primary
Quantification = Quantifier3 | Fold | Iter | LambdaDef
Expr = Quantification | Predicate
SimpleStmt = Expr | TraitApplication | Assignment | ControlFlowStmt | Import
CompoundStmt = If | For | While | RecordDefSymbol | ProcedureDefSymbol

# TODO Should we consider tuples, sets, and dicts? basically all collection operators?
ASTFieldChildren = ASTNode | list[ASTNode] | Operators
