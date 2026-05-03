from dataclasses import dataclass, fields
import pathlib
from typing_extensions import OrderedDict


from src.mod.data import ast_
from src.mod.data.symbol_table import SymbolTableError, get_primitive_types
from src.mod.data.symbol_table import SymbolTable, IdentifierContext, ScopeContext
from src.mod.data.types import (
    BaseType,
    BoolType,
    RecordType,
    ProcedureType,
    AnyType_,
    GenericType,
    DeferToSymbolTable,
    ModuleImports,
    NoneType_,
    StringType,
    IntType,
    FloatType,
    SetType,
    EnumType,
    BagType,
    RelationType,
    SequenceType,
    Trait,
    TraitCollection,
    OrderableTrait,
    IterableTrait,
    LiteralTrait,
    DomainTrait,
    MinTrait,
    MaxTrait,
    SizeTrait,
    ImmutableTrait,
    TotalOnDomainTrait,
    TotalOnRangeTrait,
    ManyToOneTrait,
    OneToManyTrait,
    EmptyTrait,
    TotalTrait,
    UniqueElementsTrait,
    GenericBoundTrait,
    TupleType,
    PairType,
    SimileTypeError,
)

from src.mod.pipeline.parser import parse, ParseError


class ParseImportError(Exception):
    pass


def populate_symbol_table(ast: ast_.ASTNode) -> SymbolTable:
    """Populates the symbol table with all identifiers in the AST.
    SIDE EFFECT: Transforms Identifiers within the ast into symbol-table assigned Symbols
    """

    symbol_table = SymbolTable()
    symbol_table.add_scope(ScopeContext.BASE)
    symbol_table_populator = PopulateSymbolTable(symbol_table)
    symbol_table_populator.populate(ast)
    return symbol_table


class PopulateSymbolTable:
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self._parents: list[ast_.ASTNode] = []

    def populate(self, ast: ast_.ASTNode) -> ast_.ASTNode:
        self._parents.append(ast)
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
                    new_list.append(self.populate(item))
                setattr(ast, f.name, new_list)
            else:
                setattr(ast, f.name, self.populate(field_value))
        self._parents.pop()
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
                self._populate_loop_parameters(iterable_names)
                _iterable_symbols = self._convert_identifier_to_symbol(iterable_names)
                _iterable = self.populate(iterable)
                _body = self.populate(body)
                self.symbol_table.pop_scope_level()

                assert isinstance(_iterable_symbols, ast_.TupleSymbol)
                return ast_.For(_iterable_symbols, _iterable, _body), False

            case ast_.QualifiedQuantifier(bound_identifiers, predicate, expression, op_type):
                assert isinstance(bound_identifiers, ast_.IdentifierListTypes)

                self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                self._populate_loop_parameters(bound_identifiers)
                _iterable_symbols = self._convert_identifier_to_symbol(bound_identifiers)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)
                self.symbol_table.pop_scope_level()

                assert isinstance(_predicate, ast_.ListOp)
                assert isinstance(_iterable_symbols, ast_.TupleSymbol)
                return ast_.QualifiedQuantifier(_iterable_symbols, _predicate, _expression, op_type), False

            case ast_.Quantifier(predicate, expression, op_type):
                self.symbol_table.add_scope(ScopeContext.QUANTIFICATION)
                unbound_identifiers = self._find_unbound_identifiers(ast)
                self._populate_loop_parameters(unbound_identifiers)
                _iterable_symbols = self._convert_identifier_to_symbol(unbound_identifiers)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)
                self.symbol_table.pop_scope_level()

                assert isinstance(_predicate, ast_.ListOp)
                assert isinstance(_iterable_symbols, ast_.TupleSymbol)
                return ast_.QualifiedQuantifier(_iterable_symbols, _predicate, _expression, op_type), False

            case ast_.ProcedureDef(name, params, body, return_type):
                params_dict: dict[str, BaseType] = OrderedDict()
                for param in params:
                    if not isinstance(param.name, ast_.Identifier):
                        raise SimileTypeError(f"Invalid procedure parameter name (must be an identifier): {param.name}", param)
                    param_type = self._ast_to_type(param.type_, True)
                    assert isinstance(param_type, BaseType), "Procedure parameters must have a valid type annotation"
                    params_dict[param.name.name] = param_type

                return_type_ = self._ast_to_type(return_type, True)
                assert isinstance(return_type_, BaseType), "Procedure return type must have a valid type annotation"
                self.symbol_table.add_symbol(
                    name.name,
                    IdentifierContext.PROCEDURE,
                    ProcedureType(params_dict, return_type_),
                )
                _name_symbol = self._convert_identifier_to_symbol(name)

                self.symbol_table.add_scope(ScopeContext.PROCEDURE)

                _params_symbols: list[ast_.Symbol] = []
                for param_name, param_type in params_dict.items():
                    self.symbol_table.add_symbol(
                        param_name,
                        IdentifierContext.PROCEDURE_PARAMETER,
                        param_type,
                    )
                    param_symbol = self._convert_identifier_to_symbol(ast_.Identifier(param_name))
                    assert isinstance(param_symbol, ast_.Symbol)
                    _params_symbols.append(param_symbol)

                _body = self.populate(body)

                self.symbol_table.pop_scope_level()
                assert isinstance(_name_symbol, ast_.Symbol)
                return ast_.ProcedureDefSymbol(_name_symbol, _params_symbols, _body), False
            case ast_.RecordDef(ast_.Identifier(name), items):
                fields: dict[str, BaseType] = OrderedDict()
                for item in items:
                    if not isinstance(item.name, ast_.Identifier):
                        raise SimileTypeError(f"Invalid struct field name (must be an identifier): {item.name}", item)
                    field_type = self._ast_to_type(item.type_, True)
                    assert isinstance(field_type, BaseType)
                    fields[item.name.name] = field_type

                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.RECORD,
                    RecordType(fields=fields),
                )

                record_scope_id = self.symbol_table.add_scope(ScopeContext.RECORD)

                field_symbols: list[ast_.Symbol] = []
                for field_name, field_type in fields.items():
                    self.symbol_table.add_symbol(
                        field_name,
                        IdentifierContext.RECORD_FIELD,
                        field_type,
                    )

                    field_symbol = self._convert_identifier_to_symbol(ast_.Identifier(field_name))
                    assert isinstance(field_symbol, ast_.Symbol)
                    field_symbols.append(field_symbol)

                self.symbol_table.pop_scope_level()

                _symbol = self._convert_identifier_to_symbol(ast_.Identifier(name))
                assert isinstance(_symbol, ast_.Symbol)
                return ast_.RecordDefSymbol(_symbol, field_symbols, record_scope_id), False
            case ast_.LambdaDef(params, predicate, expression):
                assert isinstance(params, ast_.IdentifierListTypes)

                self.symbol_table.add_scope(ScopeContext.LAMBDA)
                _predicate = self.populate(predicate)
                _expression = self.populate(expression)

                self._populate_loop_parameters(params)
                _param_symbols = self._convert_identifier_to_symbol(params)

                self.symbol_table.pop_scope_level()

                assert isinstance(_param_symbols, ast_.TupleSymbol)
                return ast_.LambdaDef(_param_symbols, _predicate, _expression), False

            # Symbols
            # TODO check for enum def in all assignment statements
            case ast_.Assignment(ast_.Identifier(name), value, with_clauses, _):
                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.VARIABLE,
                )
            case ast_.Assignment(ast_.TypedName(ast_.Identifier(name), declared_type), value, with_clauses, _):
                self.symbol_table.add_symbol(
                    name,
                    IdentifierContext.VARIABLE,
                    self._ast_to_type(declared_type),
                )
            case ast_.Import(module_file_path, import_objects):
                raise NotImplementedError("Import statements are not yet supported in the symbol table population pass")
                _populate_from_import(self.symbol_table, import_objects, module_file_path)

            # By this point, all identifiers should have been added to the symbol table
            # Replace them with symbol ids corresponding to the symbol table entry
            case ast_.Identifier(_) | ast_.MapletIdentifier(_) | ast_.TupleIdentifier(_):
                return self._convert_identifier_to_symbol(ast), False
        return None, True

    def _ast_to_type(
        self,
        ast_type: ast_.Type_ | ast_.ASTNode | ast_.None_,
        assume_generic_if_not_bound: bool = False,
    ) -> BaseType | None:
        if isinstance(ast_type, ast_.None_):
            return None
        primitive_types = get_primitive_types()

        match ast_type:
            case ast_.Identifier(name) if name in primitive_types:
                return primitive_types[name]
            case ast_.Identifier(symbol_table_name):
                symbol_table_entry = self.symbol_table.lookup_identifier_in_current_scope(symbol_table_name)
                if symbol_table_entry.declared_type is None:
                    if not assume_generic_if_not_bound:
                        raise SimileTypeError(f"Identifier {symbol_table_name} does not have a declared type in the symbol table (failed to convert ASTNode to type)", ast_type)
                    self.symbol_table.add_symbol(
                        symbol_table_name,
                        IdentifierContext.GENERIC_TYPE_PARAMETER,
                        GenericType(symbol_table_name),
                    )
                return DeferToSymbolTable(symbol_table_entry)
            case ast_.Type_(base_type, generics):
                _base_type = self._ast_to_type(base_type, assume_generic_if_not_bound)
                _concretized_generics: list[BaseType] = []
                for i, generic in enumerate(generics):
                    concretized_generic = self._ast_to_type(generic, assume_generic_if_not_bound)
                    if concretized_generic is None:
                        raise SimileTypeError(f"Generic type argument {i} cannot be None: {generics}", ast_type)
                    _concretized_generics.append(concretized_generic)

                # Fill in generic types with concrete values
                match _base_type:
                    case DeferToSymbolTable(symbol_table_entry):
                        return self._ast_to_type(
                            ast_.Type_(ast_.Identifier(symbol_table_entry.name), generics),
                            assume_generic_if_not_bound,
                        )
                    case RecordType(fields):
                        concretized_generics_index = 0
                        for field_name, field_type in fields.items():
                            if not isinstance(field_type, GenericType):
                                continue
                            if concretized_generics_index >= len(_concretized_generics):
                                raise SimileTypeError(
                                    f"Type {base_type} expects {concretized_generics_index} generic arguments, got {len(_concretized_generics)}: {_concretized_generics}", ast_type
                                )
                            fields[field_name] = _concretized_generics[concretized_generics_index]
                            concretized_generics_index += 1
                        if concretized_generics_index != len(_concretized_generics):
                            raise SimileTypeError(
                                f"Type {base_type} expects {concretized_generics_index} generic arguments, got {len(_concretized_generics)}: {_concretized_generics}", ast_type
                            )
                        return RecordType(fields, trait_collection=_base_type.trait_collection)
                    case ProcedureType(args, return_):
                        generic_type_map = {}
                        new_args = {}
                        concretized_generics_index = 0
                        for name, type_ in args.items():
                            if isinstance(type_, GenericType):
                                generic_type_map[type_.id_] = _concretized_generics[concretized_generics_index]
                                new_args[name] = _concretized_generics[concretized_generics_index]
                                concretized_generics_index += 1
                                continue
                            new_args[name] = type_
                        if concretized_generics_index != len(_concretized_generics):
                            raise SimileTypeError(
                                f"Type {_base_type} expects {concretized_generics_index} generic arguments, got {len(_concretized_generics)}: {_concretized_generics}", ast_type
                            )
                        if isinstance(return_, GenericType):
                            if return_.id_ not in generic_type_map:
                                raise SimileTypeError(
                                    f"Return type of procedure cannot be a generic type that is not also used in the argument types. Found return type {return_} with id {return_.id_} but only found generic types {generic_type_map.keys()} in the argument types",
                                    ast_type,
                                )
                            return_ = generic_type_map[return_.id_]
                        return ProcedureType(new_args, return_, trait_collection=_base_type.trait_collection)
                    case SequenceType(PairType((_, element))):
                        if len(_concretized_generics) != 1:
                            raise SimileTypeError(f"Type {_base_type} expects 1 generic argument, got {len(_concretized_generics)}: {_concretized_generics}", ast_type)
                        new_element = _concretized_generics[0]
                        return SequenceType(new_element, trait_collection=_base_type.trait_collection)
                    case BagType(PairType((element, _))):
                        if len(_concretized_generics) != 1:
                            raise SimileTypeError(f"Type {_base_type} expects 1 generic argument, got {len(_concretized_generics)}: {_concretized_generics}", ast_type)
                        new_element = _concretized_generics[0]
                        return BagType(new_element, trait_collection=_base_type.trait_collection)
                    case RelationType(PairType((left, right))):
                        if len(_concretized_generics) != 2:
                            raise SimileTypeError(f"Type {_base_type} expects 2 generic arguments, got {len(_concretized_generics)}: {_concretized_generics}", ast_type)
                        if not isinstance(left, GenericType) or not isinstance(right, GenericType):
                            raise SimileTypeError(
                                f"Only generic types can be used as attributes in type annotations, got {left} of type {type(left)} and {right} of type {type(right)}", ast_type
                            )
                        new_left, new_right = _concretized_generics
                        return PairType(new_left, new_right, trait_collection=_base_type.trait_collection)
                    case SetType(element):
                        if len(_concretized_generics) != 1:
                            raise SimileTypeError(f"Type {_base_type} expects 1 generic argument, got {len(_concretized_generics)}: {_concretized_generics}", ast_type)
                        new_element = _concretized_generics[0]
                        return SetType(new_element, trait_collection=_base_type.trait_collection)
                    case PairType((left, right)):
                        if len(_concretized_generics) != 2:
                            raise SimileTypeError(f"Type {_base_type} expects 2 generic arguments, got {len(_concretized_generics)}: {_concretized_generics}", ast_type)
                        if not isinstance(left, GenericType) or not isinstance(right, GenericType):
                            raise SimileTypeError(
                                f"Only generic types can be used as attributes in type annotations, got {left} of type {type(left)} and {right} of type {type(right)}", ast_type
                            )
                        new_left, new_right = _concretized_generics
                        return PairType(new_left, new_right, trait_collection=_base_type.trait_collection)
                    case TupleType(items):
                        if len(items) != len(_concretized_generics):
                            raise SimileTypeError(f"Type {_base_type} expects {len(items)} generic arguments, got {len(_concretized_generics)}: {_concretized_generics}", ast_type)
                        _not_none_attributes = []
                        for item, attr in zip(items, _concretized_generics):
                            if not isinstance(item, GenericType):
                                raise SimileTypeError(f"Only generic types can be used as attributes in type annotations, got {item} of type {type(item)}", ast_type)
                            _not_none_attributes.append(attr)
                        return TupleType(tuple(_not_none_attributes), trait_collection=_base_type.trait_collection)

                raise SimileTypeError(f"Failed to resolve (concretize) generic type {_base_type}", ast_type)

        raise SimileTypeError(f"Unknown type annotation: {ast_type} (failed to convert ASTNode to type)", ast_type)

    def _convert_identifier_to_symbol(self, ast: ast_.IdentifierListTypes) -> ast_.SymbolListTypes:
        match ast:
            case ast_.Identifier(name):
                symbol_table_entry = self.symbol_table.lookup_identifier_in_current_scope(name)
                return ast_.Symbol(symbol_table_entry.id_, symbol_table_entry)
            case ast_.MapletIdentifier((left, right)):
                _left = self._convert_identifier_to_symbol(left)
                _right = self._convert_identifier_to_symbol(right)
                return ast_.MapletSymbol(_left, _right)
            case ast_.TupleIdentifier(identifiers):
                _identifiers = [self._convert_identifier_to_symbol(ident) for ident in identifiers]
                return ast_.TupleSymbol(tuple(_identifiers))
        raise ValueError(f"Unsupported identifier type: {type(ast)}. This should not happen")

    def _populate_loop_parameters(self, iterable_names: ast_.IdentifierListTypes) -> None:
        if isinstance(iterable_names, ast_.Identifier):
            self.symbol_table.add_symbol(
                iterable_names.name,
                IdentifierContext.LOOP_VARIABLE,
            )
        elif isinstance(iterable_names, ast_.TupleIdentifier):
            for ident in iterable_names.flatten():
                self._populate_loop_parameters(ident)
        else:
            raise SimileTypeError(f"Invalid for loop variable name (must be an identifier, maplet identifier, or tuple identifier): {iterable_names}", iterable_names)

    def _find_unbound_identifiers(self, ast: ast_.Quantifier) -> ast_.TupleIdentifier:
        """Finds unbound identifiers in an unqualified quantifier."""
        possible_generators = list(filter(lambda x: x.op_type == ast_.BinaryOperator.IN, ast.predicate.find_all_instances(ast_.BinaryOp)))
        possible_bound_identifiers: list[ast_.IdentifierListTypes] = []
        possible_bound_identifier_names: set[ast_.Identifier] = set()
        for possible_generator in possible_generators:
            if isinstance(possible_generator.left, ast_.IdentifierListTypes):
                possible_bound_identifiers.append(possible_generator.left)
                possible_bound_identifier_names.update(possible_generator.left.flatten())

            if isinstance(possible_generator.left, ast_.BinaryOp):
                left = possible_generator.left.try_cast_maplet_to_maplet_identifier()
                if left is None:
                    continue

                possible_bound_identifiers.append(left)
                possible_bound_identifier_names.update(left.flatten())

        for possible_bound_identifier in possible_bound_identifier_names:
            if not self.symbol_table.does_symbol_exist_in_current_scope(possible_bound_identifier.name):
                possible_bound_identifiers = list(filter(lambda x: not x.contains(possible_bound_identifier), possible_bound_identifiers))

        if not possible_bound_identifiers:
            raise SimileTypeError(
                f"Failed to infer bound variables for quantifier {ast_.ast_to_source(ast)}. "
                "Either the expression is ambiguously overwriting a predefined variable in scope, "
                "or no valid generators are present in the quantification expression. Please explicitly state bound variables",
                ast,
            )

        return ast_.TupleIdentifier(tuple(possible_bound_identifiers))


def _populate_from_import(
    symbol_table: SymbolTable,
    import_objects: ast_.TupleIdentifier | ast_.None_ | ast_.ImportAll,
    module_file_path: str,
) -> None:
    # Read in imported file
    full_module_path = pathlib.Path(module_file_path).resolve(strict=True)
    with open(full_module_path, "r") as f:
        module_content = f.read()

    # Parse module content
    try:
        module_ast: ast_.Start = parse(module_content)
    except ParseError as e:
        raise ParseImportError(f"Module {module_file_path} does not contain a valid Simile module. Expected a single Start node at the top level.") from e

    if isinstance(module_ast.body, ast_.None_):
        return

    # Populate the module AST with types
    module_symbol_table = populate_symbol_table(module_ast)

    # Add module symbols to namespace
    match import_objects:
        case ast_.ImportAll():
            for symbol_table_entry in module_symbol_table.get_top_level_symbols():
                symbol_table.add_symbol(
                    symbol_table_entry.name,
                    symbol_table_entry.context,
                    symbol_table_entry.declared_type,
                )
        case ast_.None_():
            symbol_table.add_symbol(
                full_module_path.stem,
                IdentifierContext.MODULE_IMPORT,
                ModuleImports(module_symbol_table.get_top_level_symbols()),
            )
        case ast_.TupleIdentifier(identifiers):
            identifier_names = []
            for identifier in identifiers:
                if not isinstance(identifier, ast_.Identifier):
                    raise SimileTypeError(f"Invalid import type (must be an identifier): {identifier}", identifier)
                identifier_names.append(identifier.name)

            for symbol_table_entry in module_symbol_table.get_top_level_symbols():
                if symbol_table_entry.name in identifier_names:
                    symbol_table.add_symbol(
                        symbol_table_entry.name,
                        symbol_table_entry.context,
                        symbol_table_entry.declared_type,
                    )
