from dataclasses import dataclass, fields
from pathlib import Path
from typing_extensions import OrderedDict

from loguru import logger

from src.mod.data import ast_
from src.mod.data.symbol_table import (
    SymbolTable,
    IdentifierContext,
    ScopeContext,
    SymbolTableError,
    SymbolTableIdentifierEntry,
)
from src.mod.data.traits.trait_operations import MergeTraitBehaviour
from src.mod.data.types import (
    BaseType,
    BoolType,
    GenericType,
    StringType,
    IntType,
    FloatType,
    SetType,
    BagType,
    RelationType,
    SequenceType,
    TupleType,
    SimileTypeError,
    TypeOfType,
    ProcedureType,
    RecordType,
    EnumType,
    NoneType_,
    AnyType_,
    ModuleImports,
    ImportedSymbol,
    TraitType,
)
from src.mod.data.traits import LiteralTrait, MinTrait, Traits
from src.mod.data.standard_library import STANDARD_LIBRARY_FOLDER

from src.mod.data.types.primitive import NoneType_
from src.mod.data.types.set_ import EnumItemType
from src.mod.data.types.tuple_ import TupleType
from src.mod.pipeline.analysis.trait_resolver import TraitResolver
from src.mod.pipeline.parser import parse, ParseError
from src.mod.pipeline.analysis.normalize_ast import normalize_ast
from src.mod.pipeline.analysis.type_annotation_resolver import TypeAnnotationResolver
from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer


def make_symbol_table(ast: ast_.ASTNode) -> SymbolTable:
    """Populates the symbol table with all identifiers in the AST.
    SIDE EFFECT: Transforms Identifiers within the ast into symbol-table assigned Symbols
    """

    if not isinstance(ast, ast_.Start):
        raise SymbolTableError("Cannot populate symbol table because AST is not a Start node")

    # # Add in the standard library
    # if isinstance(ast.body, ast_.Statements):
    #     file_path = (STANDARD_LIBRARY_FOLDER / "standard_library.sim").resolve()
    #     standard_library_import = ast_.Import(file_path, [], ast_.ImportOperator.ALL_NAMES)
    #     ast.body.items.insert(0, standard_library_import)

    symbol_table = SymbolTable()
    symbol_table_populator = PopulateSymbolTable(symbol_table)
    try:
        symbol_table_populator.populate_base()
        symbol_table_populator.populate(ast)
    finally:
        logger.debug(symbol_table.debug())
    return symbol_table


@dataclass
class PopulateSymbolTable:
    symbol_table: SymbolTable

    BUILT_IN_TYPES = {
        # primitive
        "int": IntType(),
        "float": FloatType(),
        "string": StringType(),
        "bool": BoolType(),
        # set
        "set": SetType(GenericType()),
        "sequence": SequenceType(GenericType()),
        "bag": BagType(GenericType()),
        "relation": RelationType(GenericType(), GenericType()),
        # meta
        "generic": GenericType(),
        "type": TypeOfType(GenericType()),
        "enum": EnumType(GenericType()),
        # variable length types, dont populate anything since they can take multiple (unknown) arguments
        "tuple": TupleType([]),
        "procedure": ProcedureType(TupleType([]), GenericType()),
        "record": RecordType({}),
        # type sugar
        "ℤ": SetType(IntType()),
        "ℕ": SetType(IntType(traits=Traits({MinTrait(0)}))),
        "ℕ₁": SetType(IntType(traits=Traits({MinTrait(1)}))),
        # traits as typed objects?
        # TODO how should we handle traits as first-class objects? I suppose they should just be an expr?
        "trait": TraitType(None),
    }

    def populate_base(self) -> None:
        self.symbol_table.add_scope(ScopeContext.BASE)
        for type_name, type_ in self.BUILT_IN_TYPES.items():
            self.symbol_table.add_symbol(
                type_name,
                IdentifierContext.BUILTIN_TYPE,
                type_,
            )
        for trait_cls in TraitResolver.FLAG_TRAITS.keys() | TraitResolver.SINGLE_VALUE_TRAITS:
            self.symbol_table.add_symbol(
                trait_cls,
                IdentifierContext.BUILTIN_TRAIT,
                TraitType(trait_cls),
            )

    def populate(self, ast: ast_.ASTNode) -> ast_.ASTNode:
        assert isinstance(ast, ast_.ASTNode), f"Gotcha: {ast}"

        new_ast_node, continue_populating = self._populate_aux(ast)
        if new_ast_node is not None:
            ast = new_ast_node

        if not continue_populating:
            return ast

        for f in fields(ast):
            field_value = getattr(ast, f.name)
            if isinstance(field_value, list):
                new_list = []
                for item in field_value:
                    if not isinstance(item, ast_.ASTNode):
                        break
                    new_list.append(self.populate(item))
                else:
                    setattr(ast, f.name, new_list)
            elif isinstance(field_value, ast_.ASTNode):
                setattr(ast, f.name, self.populate(field_value))
        return ast

    def _populate_aux(self, ast: ast_.ASTNode) -> tuple[ast_.ASTNode | None, bool]:
        """Returns: (Node to replace if not None, whether to continue populating children)"""
        match ast:
            # Scopes
            case ast_.If(condition, body, else_body):
                self.symbol_table.add_scope(ScopeContext.CONDITIONAL)
                _condition = self.populate(condition)
                _body = self.populate(body)
                _else_body = self.populate(else_body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_else_body, ast_.Else | ast_.ElseIf | ast_.None_)
                return ast_.If(_condition, _body, _else_body), False

            case ast_.ElseIf(condition, body, else_body):
                self.symbol_table.add_scope(ScopeContext.CONDITIONAL)
                _condition = self.populate(condition)
                _body = self.populate(body)
                _else_body = self.populate(else_body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_else_body, ast_.Else | ast_.ElseIf | ast_.None_)
                return ast_.ElseIf(_condition, _body, _else_body), False

            case ast_.Else(body):
                self.symbol_table.add_scope(ScopeContext.CONDITIONAL)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                return ast_.Else(_body), False

            case ast_.While(condition, body):
                self.symbol_table.add_scope(ScopeContext.LOOP)
                _condition = self.populate(condition)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                return ast_.While(_condition, _body), False

            case ast_.For(iterable_names, iterable, body):
                assert isinstance(iterable_names, ast_.IdentifierListTypes)

                self.symbol_table.add_scope(ScopeContext.LOOP)
                _iterable = self.populate(iterable)
                temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
                _iterable_type = temporary_type_synthesizer.synthesize_type(iterable)
                self._populate_loop_parameters(iterable_names, _iterable_type)
                _iterable_symbols = self._convert_identifier_to_symbol(iterable_names)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_iterable_symbols, ast_.TupleSymbol)
                return ast_.For(_iterable_symbols, _iterable, _body), False

            case body if isinstance(body, ast_.QuantifierBody):
                _body = self._populate_loop_parameters_from_generators(body)
                return _body, False

            case ast_.Fold(accumulator_init, body):
                self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                _accumulator_init = self.populate(accumulator_init)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_accumulator_init, ast_.Assignment)
                assert isinstance(_body, ast_.QuantifierBody)
                return ast_.Fold(_accumulator_init, _body), False

            case ast_.IterBody(_, _) as iter_:
                return self._populate_iter(iter_), False

            case ast_.ProcedureDefIdentifier(name, params, body, return_type):
                # NOTE: param_types is populated *after* the procedure type definition since symbols must be added within the scope of the procedure
                param_types: list[BaseType] = []
                return_type_ = TypeAnnotationResolver.resolve_type_annotation(return_type, self.symbol_table)
                assert isinstance(return_type_, BaseType), "Procedure return type must have a valid type annotation"
                self.symbol_table.add_symbol(
                    name.name,
                    IdentifierContext.PROCEDURE,
                    ProcedureType(TupleType(param_types), return_type_),
                )
                _name_symbol = self._convert_identifier_to_symbol(name)

                self.symbol_table.add_scope(ScopeContext.PROCEDURE)

                _params_symbols: list[ast_.Symbol] = []
                for param in params:
                    if not isinstance(param.name, ast_.Identifier):
                        raise SimileTypeError(f"Invalid procedure parameter name (must be an identifier): {param.name}", param)
                    param_type = TypeAnnotationResolver.resolve_type_annotation(param.type_, self.symbol_table)

                    self.symbol_table.add_symbol(
                        param.name.name,
                        IdentifierContext.PROCEDURE_PARAMETER,
                        param_type,
                    )
                    param_symbol = self._convert_identifier_to_symbol(param.name)
                    assert isinstance(param_symbol, ast_.Symbol)
                    param_types.append(param_type)
                    _params_symbols.append(param_symbol)

                _body = self.populate(body)

                self.symbol_table.pop_scope_level()
                assert isinstance(_name_symbol, ast_.Symbol)
                return ast_.ProcedureDefSymbol(_name_symbol, _params_symbols, _body), False
            case ast_.RecordDefIdentifier(ast_.Identifier(name), items):
                fields: dict[str, BaseType] = OrderedDict()
                for item in items:
                    if not isinstance(item.name, ast_.Identifier):
                        raise SimileTypeError(f"Invalid struct field name (must be an identifier): {item.name}", item)
                    field_type = TypeAnnotationResolver.resolve_type_annotation(item.type_, self.symbol_table)
                    assert isinstance(field_type, BaseType)
                    fields[item.name.name] = field_type

                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.RECORD,
                    RecordType(fields=fields),
                )

                _symbol = self._convert_identifier_to_symbol(ast_.Identifier(name))
                assert isinstance(_symbol, ast_.Symbol)
                return ast_.RecordDefSymbol(_symbol, fields), False
            case ast_.LambdaDef(params, predicate, expression):
                assert isinstance(params, ast_.IdentifierListTypes)

                self.symbol_table.add_scope(ScopeContext.LAMBDA)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)

                # FIXME types are not known at this point
                self._populate_loop_parameters(params, NoneType_())
                _param_symbols = self._convert_identifier_to_symbol(params)

                self.symbol_table.pop_scope_level()

                assert isinstance(_param_symbols, ast_.TupleSymbol)
                return ast_.LambdaDef(_param_symbols, _predicate, _expression), False

            case ast_.TraitApplication(ast_.Assignment(ast_.TypedName(ast_.Identifier(name), ast_.Type_(ast_.Identifier("enum"), [])), value, is_choice), trait_asts):
                if is_choice:
                    raise SimileTypeError(f"Choice assignment cannot be used with enum definitions", ast)
                if not isinstance(value, ast_.Enumeration):
                    raise SimileTypeError(f"Enum type annotation can only be applied to enumeration definitions, got {type(value)}", value)

                members: set[str] = set()
                for _item in value.items:
                    if not isinstance(_item, ast_.Identifier):
                        raise SimileTypeError(f"Invalid enum item name (must be an identifier): {_item}", _item)
                    if self.symbol_table.symbol_exists_in_current_scope(_item.name):
                        raise SimileTypeError(f"Enum item name {_item.name} already exists in current scope, cannot be used as enum item name", _item)
                    members.add(_item.name)

                _trait_asts = [self.populate(trait) for trait in trait_asts]
                traits = TraitResolver.resolve_traits(_trait_asts, self.symbol_table)
                enum_type = EnumType(members=members, traits=traits)
                _name = self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.ENUM,
                    enum_type,
                )
                for member in members:
                    self.symbol_table.add_symbol(
                        member,
                        IdentifierContext.ENUM_ITEM,
                        EnumItemType(enum_type),
                    )
                _value = self.populate(value)
                return (
                    ast_.TraitApplication(
                        ast_.Assignment(
                            ast_.TypedName(
                                ast_.Symbol(_name),
                                ast_.Type_(ast_.Identifier("enum"), []),
                            ),
                            _value,
                            is_choice,
                        ),
                        _trait_asts,
                    ),
                    False,
                )
            case ast_.TraitApplication(ast_.Assignment(ast_.TypedName(ast_.Identifier(name), ast_.Type_(ast_.Identifier("type"), [])), value, is_choice), trait_asts):
                if is_choice:
                    raise SimileTypeError(f"Choice assignment cannot be used with type definitions", ast)
                if not isinstance(value, ast_.Type_):
                    raise SimileTypeError(f"Type definitions must have a valid type annotation (this should have been promoted by normalize_ast), got {value}", value)

                _trait_asts = [self.populate(trait) for trait in trait_asts]
                traits = TraitResolver.resolve_traits(_trait_asts, self.symbol_table)
                type_value = TypeAnnotationResolver.resolve_type_annotation(value, self.symbol_table)
                if type_value is None:
                    raise SimileTypeError(f"Type definitions must have a valid type annotation, got None", value)
                # Promote the type to a typeOfType only if it doesnt already represent a type (like generic types do represent a type value)
                # typeOfType should not wrap such objects
                type_value.traits = type_value.traits.merge_copy(traits, MergeTraitBehaviour.PREFER_LEFT)
                if not isinstance(type_value, GenericType | AnyType_ | TypeOfType):
                    type_value = TypeOfType(type_value)

                _name = self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.TYPE_NAME,
                    type_value,
                )
                if isinstance(type_value, GenericType):
                    type_value.add_symbol_info(_name)
                _value = self.populate(value)
                _type_symbol = self._convert_identifier_to_symbol(ast_.Identifier("type"))
                return (
                    ast_.TraitApplication(
                        ast_.Assignment(
                            ast_.TypedName(ast_.Symbol(_name), ast_.Type_(_type_symbol, [])),
                            _value,
                            is_choice,
                        ),
                        _trait_asts,
                    ),
                    False,
                )
            case ast_.TraitApplication(ast_.Assignment(ast_.TypedName(ast_.Identifier(name), declared_type), value, is_choice), trait_asts):
                _trait_asts = [self.populate(trait) for trait in trait_asts]
                traits = TraitResolver.resolve_traits(_trait_asts, self.symbol_table)
                _declared_type = TypeAnnotationResolver.resolve_type_annotation(declared_type, self.symbol_table)
                if _declared_type is None:
                    raise SimileTypeError(f"Variable definitions must have a valid type annotation, got None", declared_type)
                if isinstance(_declared_type, TypeOfType):
                    # Type is actually used - unwrap the TypeOfType
                    _declared_type = _declared_type.type_of
                _declared_type.traits = _declared_type.traits.merge_copy(traits, MergeTraitBehaviour.PREFER_LEFT)
                _name = self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.VARIABLE,
                    _declared_type,
                )
                _value = self.populate(value)
                _declared_type_ast = self.populate(declared_type)
                assert isinstance(_declared_type_ast, ast_.Type_)
                return (
                    ast_.TraitApplication(
                        ast_.Assignment(
                            ast_.TypedName(ast_.Symbol(_name), _declared_type_ast),
                            _value,
                            is_choice,
                        ),
                        _trait_asts,
                    ),
                    False,
                )

            case ast_.Assignment(ast_.TypedName(ast_.Identifier(name), ast_.Type_(ast_.Identifier("enum"), [])), value, is_choice_assignment):
                if is_choice_assignment:
                    raise SimileTypeError(f"Choice assignment cannot be used with enum definitions", ast)
                if not isinstance(value, ast_.Enumeration):
                    raise SimileTypeError(f"Enum type annotation can only be applied to enumeration definitions, got {type(value)}", value)

                members = set()
                for _item in value.items:
                    if not isinstance(_item, ast_.Identifier):
                        raise SimileTypeError(f"Invalid enum item name (must be an identifier): {_item}", _item)
                    if self.symbol_table.symbol_exists_in_current_scope(_item.name):
                        raise SimileTypeError(f"Enum item name {_item.name} already exists in current scope, cannot be used as enum item name", _item)
                    members.add(_item.name)

                enum_type = EnumType(members=members)
                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.ENUM,
                    enum_type,
                )
                for member in members:
                    self.symbol_table.add_symbol(
                        member,
                        IdentifierContext.ENUM_ITEM,
                        EnumItemType(enum_type),
                    )

            case ast_.Assignment(ast_.TypedName(ast_.Identifier(name), ast_.Type_(ast_.Identifier("type"), [])), value, is_choice_assignment):
                if is_choice_assignment:
                    raise SimileTypeError(f"Choice assignment cannot be used with type definitions", ast)
                if not isinstance(value, ast_.Type_):
                    raise SimileTypeError(f"Type definitions must have a valid type annotation (this should have been promoted by normalize_ast), got {value}", value)

                type_value = TypeAnnotationResolver.resolve_type_annotation(value, self.symbol_table)
                if type_value is None:
                    raise SimileTypeError(f"Type definitions must have a valid type annotation, got None", value)
                if not isinstance(type_value, GenericType | AnyType_ | TypeOfType):
                    type_value = TypeOfType(type_value)

                _name = self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.TYPE_NAME,
                    type_value,
                )
                if isinstance(type_value, GenericType):
                    type_value.add_symbol_info(_name)
                _value = self.populate(value)
                _type_symbol = self._convert_identifier_to_symbol(ast_.Identifier("type"))
                return (
                    ast_.Assignment(
                        ast_.TypedName(ast_.Symbol(_name), ast_.Type_(_type_symbol, [])),
                        _value,
                        is_choice_assignment,
                    ),
                    False,
                )
            case ast_.Assignment(ast_.TypedName(ast_.Identifier(name), declared_type), value, is_choice_assignment):
                _declared_type = TypeAnnotationResolver.resolve_type_annotation(declared_type, self.symbol_table)
                if _declared_type is None:
                    raise SimileTypeError(f"Variable definitions must have a valid type annotation, got None", declared_type)
                if isinstance(_declared_type, TypeOfType):
                    # Type is actually used - unwrap the TypeOfType
                    _declared_type = _declared_type.type_of

                _name = self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.VARIABLE,
                    _declared_type,
                )
                _value = self.populate(value)
                _declared_type_ast = self.populate(declared_type)
                assert isinstance(_declared_type_ast, ast_.Type_)
                return (
                    ast_.Assignment(
                        ast_.TypedName(ast_.Symbol(_name), _declared_type_ast),
                        _value,
                        is_choice_assignment,
                    ),
                    False,
                )
            case ast_.Import(module_file_path, names_to_import, import_operator):
                # TODO fix this to allow for modules with different names (import ... as <name>)
                module_file_path = module_file_path.with_suffix(".sim")
                module_name, module_ast = _read_from_path_and_parse(module_file_path)
                module_scope = self.symbol_table.add_scope(ScopeContext.IMPORT)
                self.populate(module_ast)
                self.symbol_table.pop_scope_level()

                match import_operator:
                    case ast_.ImportOperator.SPECIFIC_NAMES:
                        for symbol_id in module_scope.declared_symbols:
                            symbol = self.symbol_table.lookup_symbol(symbol_id, module_scope.id_)
                            if symbol.name not in names_to_import:
                                continue
                            # Skip duplicate imports from the same source (instead of throwing an error when we attempt to add duplicate symbols)
                            if self._duplicate_import(
                                IdentifierContext.MODULE_IMPORT_SYMBOL,
                                ImportedSymbol,
                                symbol.name,
                                module_file_path,
                            ):
                                continue
                            self.symbol_table.add_symbol(
                                symbol.name,
                                IdentifierContext.MODULE_IMPORT_SYMBOL,
                                ImportedSymbol(symbol, module_file_path),
                            )
                    case ast_.ImportOperator.ALL_NAMES:
                        for symbol_id in module_scope.declared_symbols:
                            symbol = self.symbol_table.lookup_symbol(symbol_id, module_scope.id_)
                            if self._duplicate_import(
                                IdentifierContext.MODULE_IMPORT_SYMBOL,
                                ImportedSymbol,
                                symbol.name,
                                module_file_path,
                            ):
                                continue
                            self.symbol_table.add_symbol(
                                symbol.name,
                                IdentifierContext.MODULE_IMPORT_SYMBOL,
                                ImportedSymbol(symbol, module_file_path),
                            )
                    case ast_.ImportOperator.MODULE_NAME:
                        if not self._duplicate_import(
                            IdentifierContext.MODULE_IMPORT,
                            ModuleImports,
                            module_name,
                            module_file_path,
                        ):

                            self.symbol_table.add_symbol(
                                module_name,
                                IdentifierContext.MODULE_IMPORT,
                                ModuleImports(module_scope, module_file_path),
                            )
                return None, False

            # By this point, all identifiers should have been added to the symbol table
            # Replace them with symbol ids corresponding to the symbol table entry
            case ast_.Identifier(_) | ast_.MapletIdentifier(_) | ast_.TupleIdentifier(_):
                return self._convert_identifier_to_symbol(ast), False
        return None, True

    def _convert_identifier_to_symbol(self, ast: ast_.IdentifierListTypes) -> ast_.SymbolListTypes:
        match ast:
            case ast_.Identifier(name):
                symbol_table_entry = self.symbol_table.lookup_identifier(name)
                return ast_.Symbol(symbol_table_entry)
            case ast_.MapletIdentifier((left, right)):
                _left = self._convert_identifier_to_symbol(left)
                _right = self._convert_identifier_to_symbol(right)
                return ast_.MapletSymbol(_left, _right)
            case ast_.TupleIdentifier(identifiers):
                _identifiers = [self._convert_identifier_to_symbol(ident) for ident in identifiers]
                return ast_.TupleSymbol(tuple(_identifiers))
        raise ValueError(f"Unsupported identifier type: {type(ast)}. This should not happen")

    def _duplicate_import(
        self,
        expected_identifier_context: IdentifierContext,
        expected_type: type[ModuleImports | ImportedSymbol],
        name: str,
        source_file: Path,
    ) -> bool:
        duplicate_symbol = self.symbol_table.get_symbol_by_name_in_current_scope(name)
        if duplicate_symbol is None:
            return False  # No clashing symbol names on this level

        return (
            duplicate_symbol.context == expected_identifier_context
            and isinstance(duplicate_symbol.declared_type, expected_type)
            and source_file == duplicate_symbol.declared_type.source_file  # type: ignore
        )

    def _populate_loop_parameters(self, iterable_names: ast_.IdentifierListTypes, corresponding_iterable_type: BaseType) -> None:
        if not isinstance(corresponding_iterable_type, SetType):
            raise SimileTypeError(f"Invalid iterable type for loop parameters (must be a set type that we can iterate over): {corresponding_iterable_type}", iterable_names)

        if isinstance(iterable_names, ast_.Identifier):
            self.symbol_table.add_symbol(
                iterable_names.name,
                IdentifierContext.LOOP_VARIABLE,
                corresponding_iterable_type.element_type,
            )
            return
        if isinstance(iterable_names, ast_.TupleIdentifier):
            if len(iterable_names.items) == 0:
                raise SimileTypeError(f"Invalid for loop variable identifier tuple (cannot be empty): {iterable_names}", iterable_names)
            if len(iterable_names.items) == 1:
                self._populate_loop_parameters(iterable_names.items[0], corresponding_iterable_type)
                return
            element_type = corresponding_iterable_type.element_type
            if not isinstance(element_type, TupleType):
                raise SimileTypeError(
                    f"Failed to destructure element type for iterable when populating loop parameters ({corresponding_iterable_type} is not a set[tuple] type)", iterable_names
                )
            if len(iterable_names.items) != len(element_type.items):
                raise SimileTypeError(
                    f"Invalid for loop variable identifier tuple (length of identifiers ({len(iterable_names.items)}) does not match element types for {element_type})",
                    iterable_names,
                )

            for ident, type_ in zip(iterable_names.items, element_type.items):
                # Rewrap in set type since we previously unwrapped to get at the tuple underneath. Kind of a hack
                self._populate_loop_parameters(ident, SetType(type_))
            return
        raise SimileTypeError(f"Invalid for loop variable name (must be an identifier, maplet identifier, or tuple identifier): {iterable_names}", iterable_names)

    def _populate_loop_parameters_from_generators(self, quantifier: ast_.QuantifierBody) -> ast_.QuantifierBody:
        match quantifier:
            case ast_.QuantifierBody([], branches) if isinstance(branches, list):
                _branches = []
                for branch in branches:
                    self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                    _branches.append(self._populate_loop_parameters_from_generators(branch))
                    self.symbol_table.pop_scope_level()
                return ast_.QuantifierBody([], _branches)
            case ast_.QuantifierBody([], expr):
                raise SimileTypeError(f"Invalid quantification - expr case {expr} must be accompanied by a generator", quantifier)
            case ast_.QuantifierBody(generators, branches) if isinstance(branches, list):
                _generators = []
                for generator in generators:
                    _generators.append(self._populate_generator(generator))
                _branches = []
                for branch in branches:
                    self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                    _branches.append(self._populate_loop_parameters_from_generators(branch))
                    self.symbol_table.pop_scope_level()
                # Need to pop scope levels added from populate generators
                for _ in _generators:
                    self.symbol_table.pop_scope_level()
                return ast_.QuantifierBody(_generators, _branches)
            case ast_.QuantifierBody(generators, expr):
                assert isinstance(expr, ast_.ASTNode), "Other case caught by earlier match case"
                _generators = []
                for generator in generators:
                    _generators.append(self._populate_generator(generator))
                _expr = self.populate(expr)
                # Need to pop scope levels added from populate generators
                for _ in _generators:
                    self.symbol_table.pop_scope_level()
                return ast_.QuantifierBody(_generators, _expr)
            case _:
                raise SimileTypeError(f"Invalid quantification - must be a list of branches or a single expression", quantifier)

    def _populate_iter(self, iter_: ast_.IterBody) -> ast_.IterBody:
        match iter_:
            case ast_.IterBody([], branches) if isinstance(branches, list):
                _branches = []
                for branch in branches:
                    self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                    _branches.append(self._populate_iter(branch))
                    self.symbol_table.pop_scope_level()
                return ast_.IterBody([], _branches)
            case ast_.IterBody([], iter_body):
                raise SimileTypeError(f"Invalid iter - iter_body case {iter_body} must be accompanied by a generator", iter_)
            case ast_.IterBody(generators, branches) if isinstance(branches, list):
                _generators = []
                for generator in generators:
                    _generators.append(self._populate_iter_generator(generator))
                _branches = []
                for branch in branches:
                    self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                    _branches.append(self._populate_iter(branch))
                    self.symbol_table.pop_scope_level()
                # Need to pop scope levels added from populate generators
                for _ in _generators:
                    self.symbol_table.pop_scope_level()
                return ast_.IterBody(_generators, _branches)
            case ast_.IterBody(generators, iter_body):
                assert isinstance(iter_body, ast_.ASTNode), "Other case caught by earlier match case"
                _generators = []
                for generator in generators:
                    _generators.append(self._populate_iter_generator(generator))
                _iter_body_return_body = self.populate(iter_body.body)
                _iter_body_return_value = self.populate(iter_body.return_value)
                # Need to pop scope levels added from populate generators
                for _ in _generators:
                    self.symbol_table.pop_scope_level()
                assert isinstance(_iter_body_return_value, ast_.SymbolListTypes)
                return ast_.IterBody(_generators, ast_.IterBodyEnd(_iter_body_return_body, _iter_body_return_value))
            case _:
                raise SimileTypeError(f"Invalid iter - must be a list of branches or a single expression", iter_)

    def _populate_generator(self, generator: ast_.Generator) -> ast_.Generator:
        """Populates a generator with the appropriate symbol table entries.
        ONLY ADDS SCOPE, SCOPE SHOULD BE POPPED AFTER THIS TO ACCOUNT FOR BRANCHING
        """
        self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
        assert isinstance(generator.identifiers, ast_.IdentifierListTypes)
        _iterable = self.populate(generator.set_)
        temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
        _iterable_type = temporary_type_synthesizer.synthesize_type(_iterable)
        self._populate_loop_parameters(generator.identifiers, _iterable_type)
        _identifier_symbols = self._convert_identifier_to_symbol(generator.identifiers)
        _predicate = self.populate(generator.predicate)
        return ast_.Generator(_identifier_symbols, _iterable, _predicate)

    def _populate_iter_generator(self, iter_generator: ast_.IterGenerator) -> ast_.IterGenerator:
        """Populates a generator with the appropriate symbol table entries.
        ONLY ADDS SCOPE, SCOPE SHOULD BE POPPED AFTER THIS TO ACCOUNT FOR BRANCHING
        """
        self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
        assert isinstance(iter_generator.generator.identifiers, ast_.IdentifierListTypes)
        temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
        _iterable = self.populate(iter_generator.generator.set_)
        _iterable_type = temporary_type_synthesizer.synthesize_type(_iterable)
        self._populate_loop_parameters(iter_generator.generator.identifiers, _iterable_type)
        _identifier_symbols = self._convert_identifier_to_symbol(iter_generator.generator.identifiers)
        _assignments: list[ast_.Assignment] = []
        for assignment in iter_generator.assignments:
            _assignment = self.populate(assignment)
            assert isinstance(_assignment, ast_.Assignment)
            _assignments.append(_assignment)
        _predicate = self.populate(iter_generator.generator.predicate)
        return ast_.IterGenerator(ast_.Generator(_identifier_symbols, _iterable, _predicate), _assignments)


def _read_from_path_and_parse(module_file_path: Path) -> tuple[str, ast_.ASTNode]:
    # Read in imported file
    try:
        full_module_path = Path(module_file_path).resolve(strict=True)
    except Exception as e:
        raise SymbolTableError(
            f"Failed to parse module for symbol table importing: module {module_file_path} does not exist according to the importing file's directory or is not a file", e
        ) from e

    if not full_module_path.is_file():
        raise SymbolTableError(f"Failed to parse module for symbol table importing: module {module_file_path} is not a file")

    with open(full_module_path, "r", encoding="utf-8") as f:
        module_content = f.read()

    # Parse module content
    try:
        module_ast: ast_.Start = parse(module_content, full_module_path)
    except ParseError as e:
        raise SymbolTableError(
            f"Failed to parse module for symbol table importing: module {module_file_path} does not contain a valid Simile module. Expected a single Start node at the top level."
        ) from e

    # And normalize ast to prep for the symb table
    try:
        normalized_module_ast = normalize_ast(module_ast)
    except Exception as e:
        raise SymbolTableError(
            f"Failed to normalize module for symbol table importing: module {module_file_path} does not contain a valid Simile module. Expected a single Start node at the top level."
        ) from e

    return full_module_path.stem, normalized_module_ast
