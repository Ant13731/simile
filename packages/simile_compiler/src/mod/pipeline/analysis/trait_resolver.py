from typing import Any, Callable, Sequence

from src.mod.data import ast_
from src.mod.data.symbol_table import SymbolTable, SymbolTableIdentifierEntry
from src.mod.data.traits import (
    SimileTraitError,
    SimileLiteralAsPythonOrderable,
    SimileLiteralAsPython,
    BaseTrait,
    ImmutableTrait,
    LiteralTrait,
    UndefinedTrait,
    GenericBoundTrait,
    OrderableTrait,
    MinTrait,
    MaxTrait,
    TreatAsExprTrait,
    OneToManyTrait,
    ManyToOneTrait,
    TotalOnDomainTrait,
    TotalOnRangeTrait,
    DomainTrait,
    IterableTrait,
    UniqueTrait,
    EmptyTrait,
    SizeTrait,
    TotalTrait,
    Traits,
)
from src.mod.pipeline.analysis.type_annotation_resolver import TypeAnnotationResolver


class TraitResolver:
    FLAG_TRAITS: dict[str, set[type[BaseTrait]]] = {
        "immutable": {ImmutableTrait},
        "undefined": {UndefinedTrait},
        "orderable": {OrderableTrait},
        "expr_procedure": {TreatAsExprTrait},
        "one_to_many": {OneToManyTrait},
        "many_to_one": {ManyToOneTrait},
        "one_to_one": {OneToManyTrait, ManyToOneTrait},
        "total_on_domain": {TotalOnDomainTrait},
        "total_on_range": {TotalOnRangeTrait},
        "iterable": {IterableTrait},
        "unique": {UniqueTrait},
        "empty": {EmptyTrait},
        "total": {TotalTrait},
    }
    SINGLE_VALUE_TRAITS: set[str] = {
        "literal",
        "minimum",
        "maximum",
        "domain",
        "size",
        "bound",
    }

    @classmethod
    def resolve_traits(cls, trait_asts: list[ast_.ASTNode], symbol_table: SymbolTable) -> Traits:
        traits = Traits()
        for trait_ast in trait_asts:
            resolved_traits = cls.resolve_trait(trait_ast, symbol_table)
            traits.update(resolved_traits)
        traits.normalize()
        return traits

    @classmethod
    def resolve_trait(cls, trait_ast: ast_.ASTNode, symbol_table: SymbolTable) -> set[BaseTrait]:
        match trait_ast:
            case ast_.Symbol(entry):
                if entry.name in cls.FLAG_TRAITS:
                    return {trait() for trait in cls.FLAG_TRAITS[entry.name]}
                raise SimileTraitError(f"Unknown trait annotation when decoding symbol: {entry.name}", trait_ast)
            case ast_.Equal(ast_.Symbol(left), right):
                # bound types are still a simile construct
                if left.name == "bound":
                    generic_bound_type = TypeAnnotationResolver.resolve_type_annotation(right, symbol_table)
                    if generic_bound_type is None:
                        raise SimileTraitError(f"Generic bound trait must have a valid type annotation, got None", right)
                    return {GenericBoundTrait((generic_bound_type,))}

                # rest of these match to python-like types for analysis
                right_literal = cls.literal_ast_to_python(right)
                match left.name:
                    case "literal":
                        return {LiteralTrait(value=right_literal)}
                    case "minimum":
                        if not isinstance(right_literal, SimileLiteralAsPythonOrderable):
                            raise SimileTraitError("Minimum trait can only be applied to orderable literals", right)
                        return {MinTrait(value=right_literal)}
                    case "maximum":
                        if not isinstance(right_literal, SimileLiteralAsPythonOrderable):
                            raise SimileTraitError("Maximum trait can only be applied to orderable literals", right)
                        return {MaxTrait(value=right_literal)}
                    case "domain":
                        if not isinstance(right_literal, frozenset | tuple):
                            raise SimileTraitError("Domain trait can only applied to literal collections", right)
                        return {DomainTrait(values=frozenset(right_literal))}
                    case "size":
                        if not isinstance(right_literal, int):
                            raise SimileTraitError("Size trait can only be applied to integer literals", right)
                        return {SizeTrait(size=right_literal)}
                raise SimileTraitError(f"Unknown trait annotation when decoding equality: {left.name}", trait_ast)

        raise SimileTraitError(f"Cannot decode trait clause structure: {trait_ast} (failed to convert ASTNode to Trait)", trait_ast)

    @classmethod
    def literal_ast_to_python(cls, literal: ast_.ASTNode) -> SimileLiteralAsPython:
        match literal:
            case ast_.None_():
                return None
            case ast_.True_():
                return True
            case ast_.False_():
                return False
            case ast_.Int(value):
                return int(value)
            case ast_.Float(value):
                return float(value)
            case ast_.String(value):
                return str(value)
            case ast_.Enumeration(items, op_type):
                converted_items = [cls.literal_ast_to_python(item) for item in items]
                if op_type in {ast_.CollectionOperator.SET, ast_.CollectionOperator.RELATION, ast_.CollectionOperator.BAG}:
                    return frozenset(converted_items)
                return tuple(converted_items)
            case ast_.TupleLiteral(items):
                converted_items = [cls.literal_ast_to_python(item) for item in items]
                return tuple(converted_items)
        raise SimileTraitError("Failed to convert Simile literal to Python object (required for trait analysis)", literal)
