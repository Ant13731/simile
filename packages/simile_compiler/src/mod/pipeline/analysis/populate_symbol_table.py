from dataclasses import dataclass, fields
from pathlib import Path
from typing_extensions import OrderedDict
from functools import singledispatchmethod
from contextlib import contextmanager

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


def make_symbol_table(ast: ast_.ASTNode, no_standard_library: bool) -> SymbolTable:
    """Populates the symbol table with all identifiers in the AST.
    SIDE EFFECT: Transforms Identifiers within the ast into symbol-table assigned Symbols
    """

    if not isinstance(ast, ast_.Start):
        raise SymbolTableError("Cannot populate symbol table because AST is not a Start node")

    # Add in the standard library
    if isinstance(ast.body, ast_.Statements) and not no_standard_library:
        file_path = (STANDARD_LIBRARY_FOLDER / "standard_library.sim").resolve()
        standard_library_import = ast_.Import(file_path, [], ast_.ImportOperator.ALL_NAMES)
        ast.body.items.insert(0, standard_library_import)

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

    def populate_base(self) -> None:
        self.symbol_table.add_scope(ScopeContext.BASE)
        for type_name, type_ in TypeAnnotationResolver.BUILT_IN_TYPES.items():
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

    @contextmanager
    def scope(self, ctx: ScopeContext):
        scope_table_entry = self.symbol_table.add_scope(ctx)
        try:
            yield scope_table_entry
        finally:
            self.symbol_table.pop_scope_level()

    @singledispatchmethod
    def _populate_aux(self, ast: ast_.ASTNode) -> tuple[ast_.ASTNode | None, bool]:
        """Returns: (Node to replace if not None, whether to continue populating children)"""
        logger.debug(f"Symbol table population not implemented for {type(ast)}")
        return None, True

    @_populate_aux.register
    def _(self, ast: ast_.If) -> tuple[ast_.ASTNode | None, bool]:
        with self.scope(ScopeContext.CONDITIONAL) as scp:
            _condition = self.populate(ast.condition)
            _body = self.populate(ast.body)
            _else_body = self.populate(ast.else_body)

        assert isinstance(_else_body, ast_.Else | ast_.ElseIf | ast_.None_)
        return ast_.If(_condition, _body, _else_body), False

    @_populate_aux.register
    def _(self, ast: ast_.ElseIf) -> tuple[ast_.ASTNode | None, bool]:
        with self.scope(ScopeContext.CONDITIONAL) as scp:
            _condition = self.populate(ast.condition)
            _body = self.populate(ast.body)
            _else_body = self.populate(ast.else_body)

        assert isinstance(_else_body, ast_.Else | ast_.ElseIf | ast_.None_)
        return ast_.ElseIf(_condition, _body, _else_body), False

    @_populate_aux.register
    def _(self, ast: ast_.Else) -> tuple[ast_.ASTNode | None, bool]:
        with self.scope(ScopeContext.CONDITIONAL) as scp:
            _body = self.populate(ast.body)

        return ast_.Else(_body), False

    @_populate_aux.register
    def _(self, ast: ast_.While) -> tuple[ast_.ASTNode | None, bool]:
        with self.scope(ScopeContext.LOOP) as scp:
            _condition = self.populate(ast.condition)
            _body = self.populate(ast.body)

        return ast_.While(_condition, _body), False

    @_populate_aux.register
    def _(self, ast: ast_.For) -> tuple[ast_.ASTNode | None, bool]:
        assert isinstance(ast.iterable_names, ast_.IdentifierListTypes)
        with self.scope(ScopeContext.LOOP) as scp:
            _iterable = self.populate(ast.iterable)
            temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
            _iterable_type = temporary_type_synthesizer.synthesize_type(ast.iterable)
            self._populate_loop_parameters(ast.iterable_names, _iterable_type)
            _iterable_symbols = self.populate(ast.iterable_names)
            _body = self.populate(ast.body)

        assert isinstance(_iterable_symbols, ast_.TupleSymbol)
        return ast_.For(_iterable_symbols, _iterable, _body), False

    @_populate_aux.register
    def _(self, ast: ast_.QuantifierBody) -> tuple[ast_.ASTNode | None, bool]:
        _generators = []
        for generator in ast.generators:
            _generator = self.populate(generator)
            assert isinstance(_generator, ast_.Generator)
            _generators.append(_generator)
        _expr = self.populate(ast.expr)
        # Need to pop scope levels added from populate generators
        for _ in _generators:
            self.symbol_table.pop_scope_level()
        return ast_.QuantifierBody(_generators, _expr), False

    @_populate_aux.register
    def _(self, ast: ast_.Generator) -> tuple[ast_.ASTNode | None, bool]:
        """Populates a generator with the appropriate symbol table entries.
        ONLY ADDS SCOPE, SCOPE SHOULD BE POPPED AFTER THIS TO ALLOW FOR THE EXPR TO USE INSCOPE VARS
        """
        self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)

        assert isinstance(ast.identifiers, ast_.IdentifierListTypes)
        _iterable = self.populate(ast.set_)
        temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
        _iterable_type = temporary_type_synthesizer.synthesize_type(_iterable)
        self._populate_loop_parameters(ast.identifiers, _iterable_type)
        _identifier_symbols = self.populate(ast.identifiers)

        _predicate = self.populate(ast.predicate)
        assert isinstance(_identifier_symbols, ast_.SymbolListTypes)
        return ast_.Generator(_identifier_symbols, _iterable, _predicate), False

    @_populate_aux.register
    def _(self, ast: ast_.Fold) -> tuple[ast_.ASTNode | None, bool]:
        with self.scope(ScopeContext.QUANTIFICATION) as scp:
            _accumulator_init = self.populate(ast.accumulator_init)
            _body = self.populate(ast.body)

        assert isinstance(_accumulator_init, ast_.Assignment)
        assert isinstance(_body, ast_.QuantifierBody)
        return ast_.Fold(_accumulator_init, _body), False

    @_populate_aux.register
    def _(self, ast: ast_.Iter) -> tuple[ast_.ASTNode | None, bool]:
        _generators = []
        for generator in ast.generators:
            _generator = self.populate(generator)
            assert isinstance(_generator, ast_.IterGenerator)
            _generators.append(_generator)
        _iter_body_return_body = self.populate(ast.body)
        _iter_body_return_value = self.populate(ast.return_value)
        # Need to pop scope levels added from populate generators
        for _ in _generators:
            self.symbol_table.pop_scope_level()
        assert isinstance(_iter_body_return_value, ast_.SymbolListTypes)
        return ast_.Iter(_generators, _iter_body_return_body, _iter_body_return_value), False

    @_populate_aux.register
    def _(self, ast: ast_.IterGenerator) -> tuple[ast_.ASTNode | None, bool]:
        """Populates a generator with the appropriate symbol table entries.
        ONLY ADDS SCOPE, SCOPE SHOULD BE POPPED AFTER THIS TO ALLOW FOR THE BODY TO USE INSCOPE VARS
        """
        self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)

        assert isinstance(ast.generator.identifiers, ast_.IdentifierListTypes)
        temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
        _iterable = self.populate(ast.generator.set_)
        _iterable_type = temporary_type_synthesizer.synthesize_type(_iterable)
        self._populate_loop_parameters(ast.generator.identifiers, _iterable_type)
        _identifier_symbols = self.populate(ast.generator.identifiers)

        _assignments: list[ast_.Assignment] = []
        for assignment in ast.assignments:
            _assignment = self.populate(assignment)
            assert isinstance(_assignment, ast_.Assignment)
            _assignments.append(_assignment)

        # Need to explicitly write out the Generator population above so that iter assignments can come before the predicate
        _predicate = self.populate(ast.generator.predicate)
        assert isinstance(_identifier_symbols, ast_.SymbolListTypes)
        return ast_.IterGenerator(ast_.Generator(_identifier_symbols, _iterable, _predicate), _assignments), False

    @_populate_aux.register
    def _(self, ast: ast_.ProcedureDefIdentifier) -> tuple[ast_.ASTNode | None, bool]:
        # NOTE: param_types is populated *after* the procedure type definition since symbols must be added within the scope of the procedure
        param_types: list[BaseType] = []
        return_type_ = TypeAnnotationResolver.resolve_type_annotation(ast.return_type, self.symbol_table)
        assert isinstance(return_type_, BaseType), "Procedure return type must have a valid type annotation"
        self.symbol_table.add_symbol(
            ast.name.name,
            IdentifierContext.PROCEDURE,
            ProcedureType(TupleType(param_types), return_type_),
        )
        _name_symbol = self.populate(ast.name)

        with self.scope(ScopeContext.PROCEDURE) as scp:
            _params_symbols: list[ast_.Symbol] = []
            for param in ast.params:
                if not isinstance(param.name, ast_.Identifier):
                    raise SimileTypeError(f"Invalid procedure parameter name (must be an identifier): {param.name}", param)
                param_type = TypeAnnotationResolver.resolve_type_annotation(param.type_, self.symbol_table)

                self.symbol_table.add_symbol(
                    param.name.name,
                    IdentifierContext.PROCEDURE_PARAMETER,
                    param_type,
                )
                param_symbol = self.populate(param.name)
                assert isinstance(param_symbol, ast_.Symbol)
                param_types.append(param_type)
                _params_symbols.append(param_symbol)

            _body = self.populate(ast.body)

        assert isinstance(_name_symbol, ast_.Symbol)
        return ast_.ProcedureDefSymbol(_name_symbol, _params_symbols, _body), False

    @_populate_aux.register
    def _(self, ast: ast_.RecordDefIdentifier) -> tuple[ast_.ASTNode | None, bool]:
        fields: dict[str, BaseType] = OrderedDict()
        record_def_type = RecordType(name=ast.name.name, fields=fields)
        self.symbol_table.add_symbol(
            ast.name.name,
            IdentifierContext.RECORD,
            record_def_type,
        )

        with self.scope(ScopeContext.RECORD) as scp:
            record_def_type.add_scope_entry(scp)
            for item in ast.items:
                if not isinstance(item.name, ast_.Identifier):
                    raise SimileTypeError(f"Invalid struct field name (must be an identifier): {item.name}", item)
                field_type = TypeAnnotationResolver.resolve_type_annotation(item.type_, self.symbol_table)
                assert isinstance(field_type, BaseType)
                fields[item.name.name] = field_type
                self.symbol_table.add_symbol(
                    item.name.name,
                    IdentifierContext.RECORD_FIELD,
                    field_type,
                )
            _symbol = self.populate(ast_.Identifier(ast.name.name))

        assert isinstance(_symbol, ast_.Symbol)
        return ast_.RecordDefSymbol(_symbol, fields), False

    @_populate_aux.register
    def _(self, ast: ast_.LambdaDef) -> tuple[ast_.ASTNode | None, bool]:
        assert isinstance(ast.params, ast_.IdentifierListTypes)
        with self.scope(ScopeContext.LAMBDA) as scp:
            _predicate = self.populate(ast.predicate)
            _expression = self.populate(ast.expression)

            # FIXME types are not known at this point
            self._populate_loop_parameters(ast.params, NoneType_())
            _param_symbols = self.populate(ast.params)

        assert isinstance(_param_symbols, ast_.TupleSymbol)
        return ast_.LambdaDef(_param_symbols, _predicate, _expression), False

    @_populate_aux.register
    def _(self, ast: ast_.TraitApplication) -> tuple[ast_.ASTNode | None, bool]:
        _trait_asts = [self.populate(trait) for trait in ast.traits]
        traits = TraitResolver.resolve_traits(_trait_asts, self.symbol_table)

        _target = self.populate(ast.target)

        match _target:
            case ast_.Assignment(ast_.TypedName(ast_.Symbol(symb), _), _, _):
                # Traits dont really apply to the actual type in a typedef
                # They apply more to the underlying type and then are wrapped in a typeOfType
                if isinstance(symb.declared_type, TypeOfType):
                    symb.declared_type.type_of.traits = symb.declared_type.type_of.traits.merge_copy(traits)
                else:
                    symb.declared_type.traits = symb.declared_type.traits.merge_copy(traits)
            case ast_.ProcedureDefSymbol(ast_.Symbol(symb), _, _):
                symb.declared_type.traits = symb.declared_type.traits.merge_copy(traits)
            case _:
                raise SimileTypeError(f"Trait application can only be applied to assignments or procedure definitions, got {_target}", ast)

        return ast_.TraitApplication(_target, _trait_asts), False

    @_populate_aux.register
    def _(self, ast: ast_.Assignment) -> tuple[ast_.ASTNode | None, bool]:
        if not isinstance(ast.target, ast_.TypedName) or not isinstance(ast.target.name, ast_.Identifier):
            return None, True

        target_name = ast.target.name.name
        declared_type_ast = ast.target.type_
        value = ast.value
        is_choice_assignment = ast.choice_assignment

        # Enum definition - closer to a record definition than an assignment
        if declared_type_ast == ast_.Type_(ast_.Identifier("enum"), []):
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
                target_name,
                IdentifierContext.ENUM,
                enum_type,
            )
            for member in members:
                self.symbol_table.add_symbol(
                    member,
                    IdentifierContext.ENUM_ITEM,
                    EnumItemType(enum_type, target_name),
                )
            return None, True

        # Type definition
        if declared_type_ast == ast_.Type_(ast_.Identifier("type"), []):
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
                target_name,
                IdentifierContext.TYPE_NAME,
                type_value,
            )
            if isinstance(type_value, GenericType):
                type_value.add_symbol_info(_name)
            _value = self.populate(value)
            _type_symbol = self.populate(ast_.Identifier("type"))
            return (
                ast_.Assignment(
                    ast_.TypedName(ast_.Symbol(_name), ast_.Type_(_type_symbol, [])),
                    _value,
                    is_choice_assignment,
                ),
                False,
            )

        # Regular assignment
        _declared_type = TypeAnnotationResolver.resolve_type_annotation(declared_type_ast, self.symbol_table)
        if _declared_type is None:
            raise SimileTypeError(f"Variable definitions must have a valid type annotation, got None", declared_type_ast)
        if isinstance(_declared_type, TypeOfType):
            # TypeOfType is unwrapped when used as a type annotation for a variable
            # TODO check if this extra logic is needed in records and procedure defs (or any type annotation instance)
            # Need to keep this distinct from the actual type within the symbol table so we distinguish the type itself from an instance of the type
            _declared_type = _declared_type.type_of

        _name = self.symbol_table.add_symbol(
            target_name,
            IdentifierContext.VARIABLE,
            _declared_type,
        )
        _value = self.populate(value)
        _declared_type_ast = self.populate(declared_type_ast)
        assert isinstance(_declared_type_ast, ast_.Type_)
        return (
            ast_.Assignment(
                ast_.TypedName(ast_.Symbol(_name), _declared_type_ast),
                _value,
                is_choice_assignment,
            ),
            False,
        )

    @_populate_aux.register
    def _(self, ast: ast_.Import) -> tuple[ast_.ASTNode | None, bool]:
        # TODO fix this to allow for modules with different names (import ... as <name>)
        module_file_path = ast.module_file_path.with_suffix(".sim")
        module_name, module_ast = _read_from_path_and_parse(module_file_path)
        module_scope = self.symbol_table.add_scope(ScopeContext.IMPORT)
        self.populate(module_ast)
        self.symbol_table.pop_scope_level()

        match ast.operator:
            case ast_.ImportOperator.SPECIFIC_NAMES:
                for symbol_id in module_scope.declared_symbols:
                    symbol = self.symbol_table.lookup_symbol(symbol_id, module_scope.id_)
                    if symbol.name not in ast.import_objects:
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
    @_populate_aux.register
    def _(self, ast: ast_.Identifier) -> tuple[ast_.ASTNode | None, bool]:
        symbol_table_entry = self.symbol_table.lookup_identifier(ast.name)
        return ast_.Symbol(symbol_table_entry), False

    @_populate_aux.register
    def _(self, ast: ast_.TupleIdentifier) -> tuple[ast_.ASTNode | None, bool]:
        _items = []
        for item in ast.items:
            _item = self.populate(item)
            assert isinstance(_item, ast_.SymbolListTypes)
            _items.append(_item)
        return ast_.TupleSymbol(tuple(_items)), False

    @_populate_aux.register
    def _(self, ast: ast_.Access) -> tuple[ast_.ASTNode | None, bool]:
        if not isinstance(ast.field, ast_.Identifier):
            return None, True
        populated_record = self.populate(ast.record)
        temporary_type_synthesizer = TypeSynthesizer(self.symbol_table)
        target_type = temporary_type_synthesizer.synthesize_type(populated_record)

        # We have a few different uses for the Access notation: modules, records, and tuples.
        # Only records need special handling of symbols since they are defined in their own scope
        if isinstance(target_type, RecordType):
            field_symbol_entry = self.symbol_table.lookup_identifier(
                ast.field.name,
                include_scope=target_type.lookup_scope_entry,
            )
            return ast_.Access(populated_record, ast_.Symbol(field_symbol_entry)), False
        return None, True

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
        logger.debug(e)
        raise SymbolTableError(
            f"Failed to parse module for symbol table importing: module {module_file_path} does not contain a valid Simile module. Failed to parse the module content."
        ) from e

    # And normalize ast to prep for the symb table
    try:
        normalized_module_ast = normalize_ast(module_ast)
    except Exception as e:
        raise SymbolTableError(
            f"Failed to normalize module for symbol table importing: module {module_file_path} does not contain a valid Simile module. Failed to normalize the imported AST."
        ) from e

    return full_module_path.stem, normalized_module_ast
