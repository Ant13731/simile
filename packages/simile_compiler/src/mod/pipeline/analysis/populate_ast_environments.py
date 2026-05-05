from __future__ import annotations
from dataclasses import dataclass, field, is_dataclass
import pathlib
from typing import TypeVar
from warnings import deprecated

from src.mod.pipeline.scanner import Location
from src.mod.pipeline.parser import parse, ParseError
from src.mod.data import ast_
from src.mod.data.ast_.symbol_table_types import (
    SimileType,
    ModuleImports,
    ProcedureTypeDef,
    StructTypeDef,
    EnumTypeDef,
    SimileTypeError,
    BaseSimileType,
    DeferToSymbolTable,
    GenericType,
)

T = TypeVar("T", bound=ast_.ASTNode)


@deprecated("Moving to external symbol table")
class ParseImportError(Exception):
    pass


@deprecated("Moving to external symbol table")
def populate_ast_environments(ast: T, current_env: ast_.SymbolTableEnvironment | None = None) -> T:
    """Attach a symbol table to the AST."""
    ast = add_environments_to_ast(ast, current_env)
    _populate_ast_environments_aux(ast)
    return ast


@deprecated("Moving to external symbol table")
def add_environments_to_ast(ast: T, current_env: ast_.SymbolTableEnvironment | None = None) -> T:
    """Helper to establish empty environments in all statement "blocks" of the AST"""
    if current_env is None:
        current_env = ast_.STARTING_ENVIRONMENT

    def add_environments_to_ast_aux(node: ast_.ASTNode) -> None:
        nonlocal current_env
        # Quantifier acts like an implicit for-loop when binding iterator variables, but does not explicitly call upon Statements in its body
        if isinstance(node, ast_.Statements | ast_.Quantifier):
            current_env = ast_.SymbolTableEnvironment(previous=current_env)
            node._env = current_env
            for child in node.children(True):
                add_environments_to_ast_aux(child)

            assert current_env.previous is not None, "Environment stack should not be empty after processing Statements node"
            current_env = current_env.previous  # type: ignore
            return

        node._env = current_env
        for child in node.children(True):
            add_environments_to_ast_aux(child)

    add_environments_to_ast_aux(ast)
    return ast


@deprecated("Moving to external symbol table")
def _populate_ast_environments_aux(node: ast_.ASTNode) -> None:
    if not isinstance(node, ast_.ASTNode):
        raise TypeError(f"Expected ASTNode in ast environment population, got {type(node)}")
    if not node._env:
        raise SimileTypeError("AST node environment is not set. Ensure environments are added before type analysis.", node)

    match node:
        case ast_.Assignment(target, value):
            _populate_ast_environments_aux(value)
            _populate_from_assignment(node, target, value)

        case ast_.For(iterable_names, iterable, body):
            if not isinstance(iterable.get_type, ast_.SetType):
                raise SimileTypeError(f"Expected iterable to be a SetType, got {iterable.get_type} (in For loop)", iterable)
            type_of_iterable_elements = iterable.get_type.element_type

            # Dont support destructuring iterable contents right now - except for mapping
            if len(iterable_names.items) != 1:
                raise SimileTypeError(
                    f"Expected only one iterable name, got {len(iterable_names.items)} names: {iterable_names.items}. Iterable names may be a mapping or single identifier",
                    iterable_names,
                )
            # Iterable names need to match the type structure of the iterable
            type_of_iterable_name = iterable_names.items[0]
            if not isinstance(type_of_iterable_name, ast_.Identifier | ast_.MapletIdentifier):
                raise SimileTypeError(
                    f"Expected iterable name to be a single identifier, got nested TupleIdentifier: {type_of_iterable_name} (in For loop - only maplets and single identifiers supported)",
                    type_of_iterable_name,
                )

            def match_and_assign_types(iterable_name: ast_.Identifier | ast_.MapletIdentifier, iterable_element_type: SimileType, env: ast_.SymbolTableEnvironment) -> None:
                if isinstance(iterable_name, ast_.Identifier):
                    # if env.get(iterable_name.name) is not None:
                    #     raise SimileTypeError(f"Identifier '{iterable_name.name}' already exists in the current scope")
                    env.put(iterable_name.name, iterable_element_type)
                    return

                if isinstance(iterable_name, ast_.MapletIdentifier) and isinstance(iterable_element_type, ast_.PairType):
                    if not isinstance(iterable_name.left, ast_.Identifier | ast_.MapletIdentifier) or not isinstance(iterable_name.right, ast_.Identifier | ast_.MapletIdentifier):
                        raise SimileTypeError(
                            f"Invalid iterable name structure (expected a maplet with two identifiers or binary operations): {iterable_name} (in For loop)",
                            iterable_name,
                        )
                    match_and_assign_types(iterable_name.left, iterable_element_type.left, env)
                    match_and_assign_types(iterable_name.right, iterable_element_type.right, env)
                    return

                raise SimileTypeError(
                    f"Iterable name structure does not match iterable element type structure (iterable name is a maplet but type structure is not a PairType). Got {iterable_name} and {iterable_element_type}",
                    iterable_name,
                )

            match_and_assign_types(type_of_iterable_name, type_of_iterable_elements, node._env)

            for child in body.children(True):
                _populate_ast_environments_aux(child)

        case ast_.RecordDef(ast_.Identifier(name), items):
            fields: dict[str, SimileType] = {}
            for item in items:
                if not isinstance(item.name, ast_.Identifier):
                    raise SimileTypeError(f"Invalid struct field name (must be an identifier): {item.name}", item)
                fields[item.name.name] = item.type_.get_type

            node._env.put(
                name,
                StructTypeDef(fields=fields),
            )
        case ast_.ProcedureDef(ast_.Identifier(name), args, body, return_type):
            assert (
                body._env is not None
            ), f"Procedure body at {node.get_location()} should have an environment - ensure add_empty_environments_to_ast was called before populating environments"

            arg_types = {}
            for arg in args:
                if not isinstance(arg.name, ast_.Identifier):
                    raise SimileTypeError(f"Invalid procedure argument name (must be an identifier): {arg.name}", arg)
                arg_types[arg.name.name] = arg.get_type

            node._env.put(
                name,
                ProcedureTypeDef(
                    arg_types=arg_types,
                    return_type=return_type.get_type,
                ),
            )

            # Populate the environment for the procedure body, using argument definition
            for arg_name, arg_type in arg_types.items():
                body._env.put(arg_name, arg_type)
            _populate_ast_environments_aux(body)

        case ast_.Quantifier(predicate, expression, op_type):
            # FIXME actually check for types between predicate and bound identifiers - right now we just use a generic type
            # idea - look for occurrence of generator within the predicate. If none or conflicting generators exist, then we know the expression is not well-formed
            for identifier in node.flatten_bound_identifiers():
                # print("Adding bound identifier to environment:", identifier.name)
                node._env.put(identifier.name, GenericType("T"))

            _populate_ast_environments_aux(predicate)
            _populate_ast_environments_aux(expression)

        case ast_.Import(module_file_path, import_objects):
            _populate_from_import(node, import_objects, module_file_path)

        case _:
            for child in node.children(True):
                _populate_ast_environments_aux(child)


@deprecated("Moving to external symbol table")
def _check_and_add_for_enum(node: ast_.ASTNode, name: str, value: ast_.ASTNode) -> tuple[bool, str]:
    """Returns True if the enum was added, False if its name/builtup identifiers already exists. When False, a reason is provided"""
    if node._env is None:
        return False, "Enum check node should have an environment - ensure add_empty_environments_to_ast was called before populating environments"

    if not isinstance(value, ast_.Enumeration):
        return False, f"Value for enum '{name}' is not a valid enumeration"

    if node._env.get(name) is not None:
        return False, f"Enum '{name}' is already defined in the current scope as {node._env.get(name)}"

    # Check if all items are identifiers
    items_to_add: set[str] = set()
    for item in value.items:
        if not isinstance(item, ast_.Identifier):
            return False, f"Enum '{name}' contains non-identifier items: {item} (expected all items to be identifiers)"
        if node._env.get(item.name) is not None:
            return False, f"Enum '{name}' contains item '{item.name}' which is already defined in the current scope as {node._env.get(item.name)}"
        items_to_add.add(item.name)

    # Add the enum to the environment
    node._env.put(name, EnumTypeDef(element_type=BaseSimileType.String, members=items_to_add))
    for item_ in items_to_add:
        node._env.put(item_, DeferToSymbolTable(name))
    return True, ""


@deprecated("Moving to external symbol table")
def _populate_from_assignment(node: ast_.ASTNode, target: ast_.ASTNode, value: ast_.ASTNode) -> None:
    assert node._env is not None, "Assignment node should have an environment - ensure add_empty_environments_to_ast was called before populating environments"

    match target:
        case ast_.Identifier(name):
            added_enum, reason = _check_and_add_for_enum(node, name, value)
            if not added_enum:
                node._env.put(target.name, value.get_type)
        case ast_.TypedName(ast_.Identifier(name), explicit_type):
            if node._env.get(name) is not None and not explicit_type.get_type.is_sub_type(node._env.get(name)):  # type: ignore
                raise SimileTypeError(f"Type mismatch: cannot assign explicit type {explicit_type} to {node._env.get(name)} (type clashes with a previous definition)", node)
            # if value.get_type != explicit_type.get_type:
            #     raise SimileTypeError(f"Type mismatch: cannot assign value of type {value.get_type} to explicit type {explicit_type}", value)

            if isinstance(explicit_type, ast_.Identifier) and explicit_type.name == "enum":  # should look like ... : enum = ...
                if value.get_type != explicit_type.get_type:
                    raise SimileTypeError(f"Type mismatch: cannot assign value of type {value.get_type} to explicit type {explicit_type}", value)

                added_enum, reason = _check_and_add_for_enum(node, name, value)
                if not added_enum:
                    raise SimileTypeError(f"Enum assignment failed: {reason}", node)
            else:
                node._env.put(name, explicit_type.get_type)

        case ast_.StructAccess(struct, field):
            assign_names = [field.name]
            while isinstance(struct, ast_.StructAccess):
                assign_names = [struct.field_name.name] + assign_names
                struct = struct.struct
            if not isinstance(struct, ast_.Identifier):
                raise SimileTypeError(f"Invalid struct access for assignment (can only assign to identifiers): {struct}", struct)

            node._env.put_nested_struct(assign_names, value.get_type)
        case ast_.TypedName(ast_.StructAccess(struct, field), explicit_type):
            if value.get_type != explicit_type.get_type:
                raise SimileTypeError(f"Type mismatch: cannot assign value of type {value.get_type} to explicit type {explicit_type}", value)

            assign_names = [field.name]
            while isinstance(struct, ast_.StructAccess):
                assign_names = [struct.field_name.name] + assign_names
                struct = struct.struct
            if not isinstance(struct, ast_.Identifier):
                raise SimileTypeError(f"Invalid struct access for assignment (can only assign to identifiers): {struct}", struct)

            node._env.put_nested_struct(assign_names, value.get_type)
        case _:
            raise SimileTypeError(f"Unsupported assignment target type: {type(target)} (expected Identifier or StructAccess or TypedName counterparts)", target)


@deprecated("Moving to external symbol table")
def _populate_from_import(
    node: ast_.ASTNode,
    import_objects: ast_.TupleIdentifier | ast_.None_ | ast_.ImportAll,
    module_file_path: str,
) -> None:
    assert node._env is not None, "Import node should have an environment - ensure add_empty_environments_to_ast was called before populating environments"

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
    module_ast_with_types = populate_ast_environments(module_ast)
    if isinstance(module_ast_with_types.body, ast_.None_):
        return
    assert module_ast_with_types.body._env is not None, "Module AST body should have an environment after populating with types"
    if module_ast_with_types.body._env is None:
        # Empty parse tree in module file
        return

    assert isinstance(module_ast_with_types.body._env, ast_.SymbolTableEnvironment), "Module AST body should have an environment"

    # Add module symbols to namespace
    match import_objects:
        case ast_.ImportAll():
            for name, symbol in module_ast_with_types.body._env.table.items():
                node._env.put(name, symbol)
        case ast_.None_():
            node._env.put(
                full_module_path.stem,
                ModuleImports(module_ast_with_types.body._env.table),
            )
        case ast_.TupleIdentifier(identifiers):
            identifier_names = []
            for identifier in identifiers:
                if not isinstance(identifier, ast_.Identifier):
                    raise SimileTypeError(f"Invalid import identifier (must be an identifier): {identifier}", identifier)
                identifier_names.append(identifier.name)

            for name, symbol in module_ast_with_types.body._env.table.items():
                if name in identifier_names:
                    node._env.put(name, symbol)
