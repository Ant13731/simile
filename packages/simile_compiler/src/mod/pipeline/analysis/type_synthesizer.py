from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any, Sequence
from functools import singledispatchmethod, reduce

from src.mod.data import ast_, types, traits
from src.mod.data.symbol_table import SymbolTable, IdentifierContext
from src.mod.data.types.typing_rule_decorator import typing_rule
from src.mod.pipeline.analysis.trait_resolver import TraitResolver
from src.mod.pipeline.analysis.type_annotation_resolver import TypeAnnotationResolver


@dataclass
class TypeSynthesizer:
    symbol_table: SymbolTable

    def type_check(self, ast: ast_.ASTNode):

        # TODO make sure the values of types match their declarations
        for node in ast.children():
            if isinstance(node, ast_.ASTNode):
                self.type_check(node)
                self.synthesize_type(node)

    @singledispatchmethod
    def synthesize_type(self, ast: ast_.ASTNode) -> types.BaseType:
        if not isinstance(ast, ast_.ASTNode):
            raise TypeError(f"Expected ASTNode for type synthesis, got {type(ast)}")
        raise NotImplementedError(f"Type checking not implemented for AST node of type {type(ast)} at location {ast.get_location()}")

    @typing_rule("Fetch Identifier")
    @synthesize_type.register
    def _(self, ast: ast_.Symbol) -> types.BaseType:
        symbol_info = self.symbol_table.lookup_symbol(ast.symbol_table_entry.id_, ast.symbol_table_entry.scope)
        if symbol_info.declared_type is None:
            raise types.SimileTypeError(f"Symbol table entry {ast.symbol_table_entry} does not have an assigned type during type resolution", ast)
        # FIXME hack to get around star-imported symbols in the namespace.
        # We need this wrapper type to dedupe in populate_symbol_table,
        # but we want the type to actually come through in the synthesizer
        # (so we can actually type check against other types)
        # The real fix would be to not need to wrap imported symbols in a new type... but we will see for now
        if isinstance(symbol_info.declared_type, types.ImportedSymbol):
            return symbol_info.declared_type.imported_symbol_entry.declared_type
        return symbol_info.declared_type

    @typing_rule("Tuple Enumeration")
    @synthesize_type.register
    def _(self, ast: ast_.TupleSymbol) -> types.BaseType:
        ast_types = [self.synthesize_type(item) for item in ast.items]
        return types.TupleType(ast_types)

    @synthesize_type.register
    def _(self, ast: ast_.Type_) -> types.BaseType:
        return TypeAnnotationResolver.resolve_type_annotation(ast, self.symbol_table)

    @synthesize_type.register
    def _(self, ast: ast_.TypedName) -> types.BaseType:
        return self.synthesize_type(ast.type_)

    @synthesize_type.register
    def _(self, ast: ast_.TraitApplication) -> types.BaseType:
        base_type = self.synthesize_type(ast.target)
        newly_applied_traits = TraitResolver.resolve_traits(ast.traits, self.symbol_table)
        base_type.traits = base_type.traits.merge_copy(newly_applied_traits, traits.MergeTraitBehaviour.PREFER_LEFT)
        return base_type

    @typing_rule("")
    @synthesize_type.register
    def _(self, ast: ast_.Int) -> types.BaseType:
        literal_value = TraitResolver.literal_ast_to_python(ast)
        return types.IntType(traits=traits.Traits({traits.LiteralTrait(literal_value)}))

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Float) -> types.BaseType:
        literal_value = TraitResolver.literal_ast_to_python(ast)
        return types.FloatType(traits=traits.Traits({traits.LiteralTrait(literal_value)}))

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.String) -> types.BaseType:
        literal_value = TraitResolver.literal_ast_to_python(ast)
        return types.StringType(traits=traits.Traits({traits.LiteralTrait(literal_value)}))

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.True_) -> types.BaseType:
        literal_value = TraitResolver.literal_ast_to_python(ast)
        return types.BoolType(traits=traits.Traits({traits.LiteralTrait(literal_value)}))

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.False_) -> types.BaseType:
        literal_value = TraitResolver.literal_ast_to_python(ast)
        return types.BoolType(traits=traits.Traits({traits.LiteralTrait(literal_value)}))

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.None_) -> types.BaseType:
        return types.NoneType_(traits=traits.Traits({traits.LiteralTrait(None)}))

    @typing_rule("Lambda Expression")
    @synthesize_type.register
    def _(self, ast: ast_.LambdaDef) -> types.BaseType:
        param_types = []
        for arg in ast.params.items:
            assert isinstance(arg, ast_.Symbol), "LambdaDef parameters must be Symbols"
            param_types.append(self.synthesize_type(arg))

        assert isinstance(self.synthesize_type(ast.predicate), types.BoolType), "Predicate of LambdaDef must be of type BoolType"
        return_type = self.synthesize_type(ast.expression)

        return types.ProcedureType(types.TupleType(list(param_types)), return_type=return_type)

    @typing_rule("Records - Access")
    @synthesize_type.register
    def _(self, ast: ast_.RecordAccess) -> types.BaseType:
        ast_type = self.synthesize_type(ast.record)
        if isinstance(ast_type, types.RecordType):
            return ast_type.access(ast.field_name.name)
        raise types.SimileTypeError(f"Cannot access field of non-record type {ast_type} in record access", ast)

    @typing_rule("Command - Procedure Call", "Relation Operations - Function Call")
    @synthesize_type.register
    def _(self, ast: ast_.Call) -> types.BaseType:
        ast_type = self.synthesize_type(ast.target)
        if isinstance(ast_type, types.ProcedureType):
            return ast_type.call([self.synthesize_type(arg) for arg in ast.args])
        if isinstance(ast_type, types.RelationType) and len(ast.args) == 1:
            return ast_type.function_call(self.synthesize_type(ast.args[0]))
        raise types.SimileTypeError(f"Cannot call type {ast_type} (expected procedure or relation)", ast)

    @typing_rule("Bag Operations - Image", "Relation Operations - Image")
    @synthesize_type.register
    def _(self, ast: ast_.Image) -> types.BaseType:
        if len(ast.indices) != 1:
            raise types.SimileTypeError(f"Image operation expects exactly one index, got {len(ast.indices)}", ast)
        ast_index = ast.indices[0]
        target_type = self.synthesize_type(ast.target)
        index_type = self.synthesize_type(ast_index)
        if isinstance(target_type, types.BagType):
            return target_type.image(index_type)
        if isinstance(target_type, types.RelationType):
            return target_type.image(index_type)
        raise types.SimileTypeError(f"Cannot take image of non-relation type {target_type}", ast)

    # There should be no types or typed names
    # @resolve_type.register
    # def _(self, ast: ast_.Type_) -> types.BaseType: ...
    # @resolve_type.register
    # def _(self, ast: ast_.TypedName) -> types.BaseType: ...

    @typing_rule("Command - return")
    @synthesize_type.register
    def _(self, ast: ast_.Return) -> types.BaseType:
        return self.synthesize_type(ast.value)

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Assignment) -> types.BaseType:
        return types.NoneType_()

    @typing_rule("Command - break", "Command - continue", "Command - skip")
    @synthesize_type.register
    def _(self, ast: ast_.ControlFlowStmt) -> types.BaseType:
        return types.NoneType_()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.If | ast_.ElseIf | ast_.Else | ast_.For | ast_.While) -> types.BaseType:
        return types.NoneType_()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Import | ast_.Start | ast_.Statements) -> types.BaseType:
        return types.NoneType_()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.RecordDefSymbol | ast_.ProcedureDefSymbol) -> types.BaseType:
        return types.NoneType_()

    @typing_rule("Binary Boolean Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Implies) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.BoolType, types.BoolType.implies)

    @typing_rule("Binary Boolean Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Equivalent) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.BoolType, types.BoolType.equivalent)

    @typing_rule("Binary Boolean Operations")
    @synthesize_type.register
    def _(self, ast: ast_.NotEquivalent) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.BoolType, types.BoolType.not_equivalent)

    @typing_rule("Bag Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Add) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.add),
                (ast, types.FloatType, types.FloatType.add),
                (ast, types.BagType, types.BagType.bag_add),
            ]
        )

    @typing_rule("Bag Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Subtract) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.subtract),
                (ast, types.FloatType, types.FloatType.subtract),
                (ast, types.BagType, types.BagType.bag_difference),
            ]
        )

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Multiply) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.multiply),
                (ast, types.FloatType, types.FloatType.multiply),
            ]
        )

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Divide) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.divide),
                (ast, types.FloatType, types.FloatType.divide),
            ]
        )

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.IntDivide) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.IntType, types.IntType.int_divide)

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Modulo) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.IntType, types.IntType.modulo)

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Exponent) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.power),
                (ast, types.FloatType, types.FloatType.power),
            ]
        )

    @typing_rule("Ordering Operators")
    @synthesize_type.register
    def _(self, ast: ast_.LessThan) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.less_than),
                (ast, types.FloatType, types.FloatType.less_than),
            ]
        )

    @typing_rule("Ordering Operators")
    @synthesize_type.register
    def _(self, ast: ast_.LessThanOrEqual) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.less_than_equals),
                (ast, types.FloatType, types.FloatType.less_than_equals),
            ]
        )

    @typing_rule("Ordering Operators")
    @synthesize_type.register
    def _(self, ast: ast_.GreaterThan) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.greater_than),
                (ast, types.FloatType, types.FloatType.greater_than),
            ]
        )

    @typing_rule("Ordering Operators")
    @synthesize_type.register
    def _(self, ast: ast_.GreaterThanOrEqual) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.IntType, types.IntType.greater_than_equals),
                (ast, types.FloatType, types.FloatType.greater_than_equals),
            ]
        )

    @typing_rule("Equals")
    @synthesize_type.register
    def _(self, ast: ast_.Equal) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.BaseType, types.BaseType.equals)

    @typing_rule("Equals")
    @synthesize_type.register
    def _(self, ast: ast_.NotEqual) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.BaseType, types.BaseType.not_equals)

    # @resolve_type.register
    # def _(self, ast: ast_.Is) -> types.BaseType:
    # @resolve_type.register
    # def _(self, ast: ast_.IsNot) -> types.BaseType:

    @typing_rule("Set Membership")
    @synthesize_type.register
    def _(self, ast: ast_.In) -> types.BaseType:
        return self._synthesize_type_binary_right_as_base(ast, types.SetType, types.SetType.in_)

    @typing_rule("Set Membership")
    @synthesize_type.register
    def _(self, ast: ast_.NotIn) -> types.BaseType:
        return self._synthesize_type_binary_right_as_base(ast, types.SetType, types.SetType.not_in)

    @typing_rule("Set Operations", "Bag Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Union) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.SetType, types.SetType.union),
                (ast, types.BagType, types.BagType.bag_union),
            ]
        )

    @typing_rule("Set Operations", "Bag Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Intersection) -> types.BaseType:
        return self._synthesize_type_multiple_binary_paths(
            [
                (ast, types.SetType, types.SetType.intersection),
                (ast, types.BagType, types.BagType.bag_intersection),
            ]
        )

    @typing_rule("Set Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Difference) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.difference)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Subset) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.is_subset)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.SubsetEq) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.is_subset_equals)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Superset) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.is_superset)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.SupersetEq) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.is_superset_equals)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.NotSubset) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.not_is_subset)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.NotSubsetEq) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.not_is_subset_equals)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.NotSuperset) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.not_is_superset)

    @typing_rule("Set Ordering Operations")
    @synthesize_type.register
    def _(self, ast: ast_.NotSupersetEq) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.not_is_superset_equals)

    @typing_rule("Maplet")
    @synthesize_type.register
    def _(self, ast: ast_.Maplet) -> types.BaseType:
        return types.PairType.maplet(self.synthesize_type(ast.left), self.synthesize_type(ast.right))

    @typing_rule("Relation Operations - Overriding")
    @synthesize_type.register
    def _(self, ast: ast_.RelationOverriding) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.RelationType, types.RelationType.overriding)

    @typing_rule("Relation Operations - Composition")
    @synthesize_type.register
    def _(self, ast: ast_.Composition) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.RelationType, types.RelationType.composition)

    @typing_rule("Cartesian Product")
    @synthesize_type.register
    def _(self, ast: ast_.CartesianProduct) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SetType, types.SetType.cartesian_product)

    @typing_rule("Numerical Range")
    @synthesize_type.register
    def _(self, ast: ast_.Upto) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.IntType, types.IntType.upto)

    @typing_rule("Sequence Operations - Concatenation")
    @synthesize_type.register
    def _(self, ast: ast_.Concat) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.SequenceType, types.SequenceType.concat)

    @typing_rule("Relation Operations - Domain Subtraction")
    @synthesize_type.register
    def _(self, ast: ast_.DomainSubtraction) -> types.BaseType:
        return self._synthesize_type_binary_right_as_base(ast, types.RelationType, types.RelationType.domain_subtraction)

    @typing_rule("Relation Operations - Domain Restriction")
    @synthesize_type.register
    def _(self, ast: ast_.DomainRestriction) -> types.BaseType:
        return self._synthesize_type_binary_right_as_base(ast, types.RelationType, types.RelationType.domain_restriction)

    @typing_rule("Relation Operations - Range Subtraction")
    @synthesize_type.register
    def _(self, ast: ast_.RangeSubtraction) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.RelationType, types.RelationType.range_subtraction)

    @typing_rule("Relation Operations - Range Restriction")
    @synthesize_type.register
    def _(self, ast: ast_.RangeRestriction) -> types.BaseType:
        return self._synthesize_type_binary(ast, types.RelationType, types.RelationType.range_restriction)

    def create_relation_type(self, ast: ast_.RelationOp, relation_operator: ast_.RelationOperator) -> types.BaseType:
        left_type = self.synthesize_type(ast.left)
        right_type = self.synthesize_type(ast.right)
        relation_type = types.RelationType(left_type, right_type)
        relation_type.apply_traits_from_relation_operator(relation_operator)
        return relation_type

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Relation) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.RELATION)

    @typing_rule("Relation Subtype - Total Relation")
    @synthesize_type.register
    def _(self, ast: ast_.TotalRelation) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.TOTAL_RELATION)

    @typing_rule("Relation Subtype - Surjective Relation")
    @synthesize_type.register
    def _(self, ast: ast_.SurjectiveRelation) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.SURJECTIVE_RELATION)

    @typing_rule("Relation Subtype - Total Surjective Relation")
    @synthesize_type.register
    def _(self, ast: ast_.TotalSurjectiveRelation) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.TOTAL_SURJECTIVE_RELATION)

    @typing_rule("Relation Subtype - Partial Function")
    @synthesize_type.register
    def _(self, ast: ast_.PartialFunction) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.PARTIAL_FUNCTION)

    @typing_rule("Relation Subtype - Total Function")
    @synthesize_type.register
    def _(self, ast: ast_.TotalFunction) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.TOTAL_FUNCTION)

    @typing_rule("Relation Subtype - Partial Injection")
    @synthesize_type.register
    def _(self, ast: ast_.PartialInjection) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.PARTIAL_INJECTION)

    @typing_rule("Relation Subtype - Total Injection")
    @synthesize_type.register
    def _(self, ast: ast_.TotalInjection) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.TOTAL_INJECTION)

    @typing_rule("Relation Subtype - Partial Surjection")
    @synthesize_type.register
    def _(self, ast: ast_.PartialSurjection) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.PARTIAL_SURJECTION)

    @typing_rule("Relation Subtype - Total Surjection")
    @synthesize_type.register
    def _(self, ast: ast_.TotalSurjection) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.TOTAL_SURJECTION)

    @typing_rule("Relation Subtype - Bijection")
    @synthesize_type.register
    def _(self, ast: ast_.Bijection) -> types.BaseType:
        return self.create_relation_type(ast, ast_.RelationOperator.BIJECTION)

    @typing_rule("Boolean Operations - Negation")
    @synthesize_type.register
    def _(self, ast: ast_.Not) -> types.BaseType:
        val_type = self.synthesize_type(ast.value)
        if not isinstance(val_type, types.BoolType):
            raise types.SimileTypeError(f"Operand of negation must be of type BoolType. Got {val_type}", ast.value)
        return val_type.not_()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Negative) -> types.BaseType:
        val_type = self.synthesize_type(ast.value)
        if not isinstance(val_type, types.IntType | types.FloatType):
            raise types.SimileTypeError(f"Operand of negative must be of type IntType or BoolType. Got {val_type}", ast.value)
        return val_type.negate()

    # @typing_rule("Set Operations - Powerset")
    # @synthesize_type.register
    # def _(self, ast: ast_.Powerset) -> types.BaseType:
    #     val_type = self.synthesize_type(ast.value)
    #     return types.SetType.powerset(val_type)

    # @typing_rule()
    # @synthesize_type.register
    # def _(self, ast: ast_.NonemptyPowerset) -> types.BaseType: ...
    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Inverse) -> types.BaseType:
        val_type = self.synthesize_type(ast.value)
        if not isinstance(val_type, types.RelationType):
            raise types.SimileTypeError(f"Operand of inverse must be of type RelationType. Got {val_type}", ast.value)
        return val_type.inverse()

    @typing_rule("Binary Boolean Operations")
    @synthesize_type.register
    def _(self, ast: ast_.And) -> types.BaseType:
        item_types = []
        for item in ast.items:
            item_type = self.synthesize_type(item)
            if not isinstance(item_type, types.BoolType):
                raise types.SimileTypeError(f"Operand of and_ must be of type BoolType. Got {item_type}", item)
            item_types.append(item_type)
        return reduce(types.BoolType.and_, item_types)

    @typing_rule("Binary Boolean Operations")
    @synthesize_type.register
    def _(self, ast: ast_.Or) -> types.BaseType:
        item_types = []
        for item in ast.items:
            item_type = self.synthesize_type(item)
            if not isinstance(item_type, types.BoolType):
                raise types.SimileTypeError(f"Operand of or_ must be of type BoolType. Got {item_type}", item)
            item_types.append(item_type)
        return reduce(types.BoolType.or_, item_types)

    # @typing_rule("Forall")
    # @synthesize_type.register
    # def _(self, ast: ast_.Forall) -> types.BaseType: ...
    # @typing_rule("Exists")
    # @synthesize_type.register
    # def _(self, ast: ast_.Exists) -> types.BaseType: ...
    # @typing_rule("Binds (with generator)", "Binds with OR", "Binds with AND")

    @typing_rule("Quantifier", "Branching Quantifier")
    @synthesize_type.register
    def _(self, ast: ast_.QuantifierBody) -> types.BaseType:
        self._synthesize_type_generator_nest(ast.generators)

        if isinstance(ast.end_or_branch, ast_.ASTNode):
            return_type = self.synthesize_type(ast.end_or_branch)
            return types.QuantificationBodyIntermediary(return_type)

        branch_types: list[types.BaseType] = []
        for branch in ast.end_or_branch:
            branch_type = self.synthesize_type(branch)
            if not isinstance(branch_type, types.QuantificationBodyIntermediary):
                raise types.SimileTypeError(f"Branch of quantifier must be of type QuantificationBodyIntermediary. Got {branch_type}", branch)
            branch_types.append(branch_type.return_type)

        return_type = types.BaseType.max_type(branch_types)
        return types.QuantificationBodyIntermediary(return_type)

    @typing_rule("Generator Nest")
    def _synthesize_type_generator_nest(self, generators: Sequence[ast_.Generator | ast_.IterGenerator]) -> types.BaseType:
        if len(generators) == []:
            return types.NoneType_()

        generator_types = []
        for generator in generators:
            generator_types.append(self.synthesize_type(generator))

        return types.GeneratorIntermediary(types.TupleType(generator_types))

    @typing_rule("Generator")
    @synthesize_type.register
    def _(self, ast: ast_.Generator) -> types.BaseType:
        set_type = self.synthesize_type(ast.set_)
        if not isinstance(set_type, types.SetType):
            raise types.SimileTypeError(f"Generator set must be of type SetType. Got {set_type}", ast.set_)

        assert isinstance(ast.identifiers, ast_.SymbolListTypes), "No identifiers allowed at this stage"
        self._structural_match(ast.identifiers, set_type.element_type)

        predicate_type = self.synthesize_type(ast.predicate)
        if not isinstance(predicate_type, types.BoolType):
            raise types.SimileTypeError(f"Predicate of quantifier must be of type BoolType. Got {predicate_type}", ast.predicate)

        return types.GeneratorIntermediary(set_type.element_type)

    @typing_rule("Structural Match", "Structural Match with Tuple")
    def _structural_match(self, identifiers: ast_.SymbolListTypes, element_type: types.BaseType) -> None:
        match identifiers:
            case ast_.TupleSymbol(symbols):
                if not isinstance(element_type, types.TupleType):
                    # FIXME Hack because the parser wraps single identifiers in a tupleIdentifier during the ident_list call
                    if len(symbols) == 1:
                        return self._structural_match(symbols[0], element_type)
                    raise types.SimileTypeError(f"Expected element type to be TupleType for structural match with tuple. Got {element_type}", identifiers)
                if len(symbols) != len(element_type.items):
                    raise types.SimileTypeError(
                        f"Expected number of symbols in tuple to match number of elements in tuple type. Got {len(symbols)}, {symbols} symbols and {len(element_type.items)}, {element_type.items} elements",
                        identifiers,
                    )
                for symbol, elem_type in zip(symbols, element_type.items):
                    self._structural_match(symbol, elem_type)
            case ast_.Symbol(symbol_table_entry):
                symbol_info = self.symbol_table.lookup_symbol(symbol_table_entry.id_, symbol_table_entry.scope)
                if symbol_info.context != IdentifierContext.LOOP_VARIABLE:
                    raise types.SimileTypeError(f"Expected symbol to be a loop variable for structural match. Got {symbol_info.context}", identifiers)
                symbol_info.declared_type = element_type
            case _:
                raise types.SimileTypeError("Unreachable state", identifiers)

    @typing_rule("Iter Generator")
    @synthesize_type.register
    def _(self, ast: ast_.IterGenerator) -> types.BaseType:
        generator_type = self.synthesize_type(ast.generator)
        if not isinstance(generator_type, types.GeneratorIntermediary):
            raise types.SimileTypeError(f"Iter generator must be of type GeneratorIntermediary. Got {generator_type}", ast.generator)
        for assignment in ast.assignments:
            self.synthesize_type(assignment)
        return generator_type

    @typing_rule("Iter (body)")
    @synthesize_type.register
    def _(self, ast: ast_.IterBodyEnd) -> types.BaseType:  # typecheck body, then return return_value's type
        self.synthesize_type(ast.body)
        return self.synthesize_type(ast.return_value)

    @typing_rule("Iter")
    @synthesize_type.register
    def _(self, ast: ast_.IterBody) -> types.BaseType:
        self._synthesize_type_generator_nest(ast.generators)

        if isinstance(ast.end_or_branch, ast_.ASTNode):
            return self.synthesize_type(ast.end_or_branch)

        branch_types: list[types.BaseType] = []
        for branch in ast.end_or_branch:
            branch_type = self.synthesize_type(branch)
            branch_types.append(branch_type)

        return_type = types.BaseType.max_type(branch_types)
        return return_type

    @typing_rule("Fold")
    @synthesize_type.register
    def _(self, ast: ast_.Fold) -> types.BaseType:
        self.synthesize_type(ast.accumulator_init)
        accumulator_init_var_type = self.synthesize_type(ast.accumulator_init.target)
        quantifier_body_type = self.synthesize_type(ast.quantifier_body)
        if not isinstance(quantifier_body_type, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of fold must be a quantification body. Got {quantifier_body_type}", ast.quantifier_body)

        fold_return_type = types.BaseType.max_type([accumulator_init_var_type, quantifier_body_type.return_type])
        return types.QuantificationBodyIntermediary(fold_return_type).fold()

    @typing_rule("Forall")
    @synthesize_type.register
    def _(self, ast: ast_.Forall) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of forall must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.forall()

    @typing_rule("Exists")
    @synthesize_type.register
    def _(self, ast: ast_.Exists) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.exists()

    @typing_rule("General Union")
    @synthesize_type.register
    def _(self, ast: ast_.UnionAll) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.union_all()

    @typing_rule("General Intersection")
    @synthesize_type.register
    def _(self, ast: ast_.IntersectionAll) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.intersection_all()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Sum) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.sum()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Product) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.product()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Min) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.min()

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.Max) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.max()

    @typing_rule("Set Enumeration")
    @synthesize_type.register
    def _(self, ast: ast_.SequenceEnumeration) -> types.BaseType:
        item_types = list(map(self.synthesize_type, ast.items))
        return types.SequenceType.enumeration(item_types)

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.SetEnumeration) -> types.BaseType:
        item_types = list(map(self.synthesize_type, ast.items))
        return types.SetType.enumeration(item_types)

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.RelationEnumeration) -> types.BaseType:
        item_types = list(map(self.synthesize_type, ast.items))
        return types.RelationType.enumeration(item_types)

    @typing_rule()
    @synthesize_type.register
    def _(self, ast: ast_.BagEnumeration) -> types.BaseType:
        item_types = list(map(self.synthesize_type, ast.items))
        return types.BagType.enumeration(item_types)

    # @typing_rule()
    # @synthesize_type.register
    # def _(self, ast: ast_.SequenceComprehension) -> types.BaseType: ...
    # @typing_rule()
    # @synthesize_type.register
    # def _(self, ast: ast_.SetComprehension) -> types.BaseType: ...
    # @typing_rule()
    # @synthesize_type.register
    # def _(self, ast: ast_.RelationComprehension) -> types.BaseType: ...
    # @typing_rule()
    # @synthesize_type.register
    # def _(self, ast: ast_.BagComprehension) -> types.BaseType: ...
    @typing_rule("Sequence Comprehension")
    @synthesize_type.register
    def _(self, ast: ast_.SequenceComprehension) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.sequence_comprehension()

    @typing_rule("Set Comprehension")
    @synthesize_type.register
    def _(self, ast: ast_.SetComprehension) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.set_comprehension()

    @typing_rule("Relation Comprehension")  # TODO FIXME?
    @synthesize_type.register
    def _(self, ast: ast_.RelationComprehension) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.relation_comprehension()

    @typing_rule("Bag Comprehension")
    @synthesize_type.register
    def _(self, ast: ast_.BagComprehension) -> types.BaseType:
        quantification_body = self.synthesize_type(ast.body)
        if not isinstance(quantification_body, types.QuantificationBodyIntermediary):
            raise types.SimileTypeError(f"Body of exists must be a quantification body. Got {quantification_body}", ast.body)
        return quantification_body.bag_comprehension()

    def _synthesize_type_binary[T](
        self,
        ast: ast_.BinaryOp | ast_.RelationOp,
        expected_left_type: type[T],
        operation_as_type_func: Callable[[T, types.BaseType], types.BaseType],
    ) -> types.BaseType:
        left_type = self.synthesize_type(ast.left)
        right_type = self.synthesize_type(ast.right)
        if not isinstance(left_type, expected_left_type):
            raise types.SimileTypeError(f"Left operand of {operation_as_type_func.__name__} must be of type {expected_left_type}, got {left_type}", ast.left)
        return operation_as_type_func(left_type, right_type)

    def _synthesize_type_binary_right_as_base[T](
        self,
        ast: ast_.BinaryOp | ast_.RelationOp,
        expected_right_type: type[T],
        operation_as_type_func: Callable[[T, types.BaseType], types.BaseType],
    ) -> types.BaseType:
        left_type = self.synthesize_type(ast.left)
        right_type = self.synthesize_type(ast.right)
        if not isinstance(right_type, expected_right_type):
            raise types.SimileTypeError(f"Right operand of {operation_as_type_func.__name__} must be of type {expected_right_type}, got {right_type}", ast.right)
        return operation_as_type_func(right_type, left_type)

    def _synthesize_type_multiple_binary_paths[T](
        self, type_resolution_funcs: Sequence[tuple[ast_.BinaryOp | ast_.RelationOp, type[T] | Any, Callable[[T, types.BaseType], types.BaseType]] | Any]
    ) -> types.BaseType:
        tries: list[types.SimileTypeError] = []
        for ast, expected_left_type, op_as_type_func in type_resolution_funcs:
            try:
                return self._synthesize_type_binary(ast, expected_left_type, op_as_type_func)
            except types.SimileTypeError as e:
                tries.append(e)
        raise types.SimileTypeError(f"All attempted type resolution paths failed. Got: {'\n'.join(map(str,tries))}")
