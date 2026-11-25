from __future__ import annotations
from collections import OrderedDict
from typing import Any

from loguru import logger

from src.mod.data import ast_, traits, types
from src.mod.data.helpers.dataclass import dataclass_traverse
from src.mod.data.simrw import SimrwAST, SimrwRule

from src.mod.pipeline.analysis import TypeAnnotationResolver, make_symbol_table, normalize_ast
from src.mod.pipeline.analysis.trait_resolver import TraitResolver
from src.mod.pipeline.parser import parse
from src.mod.data.simrw.guard_condition import GuardCondition, GUARD_CONDITIONS


def convert_simrw_to_rewrite_rules(rewrite_rule_asts: list[SimrwAST]) -> list[SimrwRule]:
    rewrite_rules: list[SimrwRule] = []
    for rewrite_rule_ast in rewrite_rule_asts:
        logger.debug(
            f"Converting simrw rule {rewrite_rule_ast.name} to rewrite rule (with vars {rewrite_rule_ast.vars_}): {rewrite_rule_ast.rewrite_left} ~> {rewrite_rule_ast.rewrite_right}"
        )

        # TODO how do we convert typed_vars and rewrite_left_ast into additional guard conditions?
        # Effectively need to pattern match on the structure of LH first, then further match type structures, keeping track of replaced variable names
        typed_vars: dict[str, types.BaseType] = collect_typed_vars(rewrite_rule_ast.vars_)
        rewrite_left_ast = parse(rewrite_rule_ast.rewrite_left)
        rewrite_right_ast = parse(rewrite_rule_ast.rewrite_right)
        guard_conditions = list(map(collect_guard_condition, rewrite_rule_ast.when))

        rewrite_rule = SimrwRule(
            _name=rewrite_rule_ast.name,
            vars_=typed_vars,
            rewrite_left=rewrite_left_ast,
            rewrite_right=rewrite_right_ast,
            when=guard_conditions,
        )
        rewrite_rules.append(rewrite_rule)
    return rewrite_rules


def collect_guard_condition(when_condition_str: str) -> GuardCondition:
    condition_ast = parse(when_condition_str)
    unwrapped_condition_ast = _unwrap_start_nodes(condition_ast)
    if not isinstance(unwrapped_condition_ast, ast_.Call):
        raise ValueError(f"Expected a Call AST node, got {type(unwrapped_condition_ast)}")
    if not isinstance(unwrapped_condition_ast.target, ast_.Identifier):
        raise ValueError(f"Expected a Identifier AST node on the left side of Call, got {type(unwrapped_condition_ast.target)}")
    guard_condition_name = unwrapped_condition_ast.target.name
    if guard_condition_name not in GUARD_CONDITIONS:
        raise ValueError(f"Guard condition {guard_condition_name} is not defined in GUARD_CONDITIONS")
    return GUARD_CONDITIONS[guard_condition_name](*unwrapped_condition_ast.args)


def collect_typed_vars(rewrite_rule_var_str: str) -> dict[str, types.BaseType]:
    var_ast_combined = parse(rewrite_rule_var_str)
    normalized_var_ast_combined = normalize_ast(var_ast_combined)
    if not isinstance(normalized_var_ast_combined, ast_.Start):
        raise ValueError(f"AST Normalization removed ast_.Start - this should never happen. Before: {var_ast_combined}. After: {normalized_var_ast_combined}")
    if isinstance(normalized_var_ast_combined.body, ast_.None_):
        return {}
    var_asts = normalized_var_ast_combined.body.items

    ast_vars: dict[str, ast_.Type_] = {}
    ast_var_traits: dict[str, traits.Traits | None] = {}
    trait_only_base_symbol_table = make_symbol_table(
        ast_.Start(ast_.Statements([]), ""),
        False,
    )
    for var_ast in var_asts:
        trait_collection = None
        if isinstance(var_ast, ast_.TraitApplication):
            trait_clauses = var_ast.traits
            trait_collection = TraitResolver.resolve_traits(trait_clauses, trait_only_base_symbol_table)
            var_ast = var_ast.target

        if not isinstance(var_ast, ast_.TypedName):
            raise ValueError(f"Expected a TypedName AST node, got {type(var_ast)}")
        if not isinstance(var_ast.name, ast_.Identifier):
            raise ValueError(f"Expected a Identifier AST node on the left side of TypedName, got {type(var_ast)}")
        if not isinstance(var_ast.type_, ast_.Type_):
            raise ValueError(f"Simrw vars must have a corresponding type of the form `x: type` (got: {var_ast})")
        # Unwrap and collect LH variable identifiers
        ast_vars[var_ast.name.name] = var_ast.type_
        ast_var_traits[var_ast.name.name] = trait_collection

    # Search types for identifiers of the form T[0-9]*. These identifiers are reserved for generic types
    # If one of the LH var identifiers matches T[0-9]*, throw an error (and suggest that any variable names use T_... instead)
    for var_name in ast_vars:
        if var_name.startswith("T") and var_name[1:].isdigit():
            raise ValueError(f"Variable names matching T[0-9]* (like '{var_name}') are reserved for (implicit) generic types. Please use a different name (e.g., T_...).")

    # Need to keep these loops separate bc we want to dedupe generic type defs
    generic_type_vars: list[str] = []
    for type_ast in ast_vars.values():
        generic_type_vars.extend(set(filter(None, dataclass_traverse(type_ast, _is_implicitly_defined_generic_type))))
    # cant use sets here since order matters when we determine symbols in the symbol table.
    # from_keys keeps order while eliminating duplicates
    generic_type_vars_deduped = list(OrderedDict.fromkeys(generic_type_vars))
    generic_type_assignments: list[ast_.ASTNode] = list(map(_name_to_generic_type_assignment, generic_type_vars_deduped))

    # Add required generic types to the symbol table (all other types are expected to be builtins)
    generic_symbol_table = make_symbol_table(
        ast_.Start(ast_.Statements(generic_type_assignments), rewrite_rule_var_str),
        False,
    )
    # Synthesize types for each var identifier (remember to handle traits)
    typed_vars: dict[str, types.BaseType] = {}
    for var_name, type_ast in ast_vars.items():
        trait_collection = ast_var_traits.get(var_name)
        var_type = TypeAnnotationResolver.resolve_type_annotation(type_ast, generic_symbol_table)
        if trait_collection:
            var_type.traits = var_type.traits.merge_copy(trait_collection)
        typed_vars[var_name] = var_type

    return typed_vars


def _is_implicitly_defined_generic_type(ast: Any) -> str | None:
    if not isinstance(ast, ast_.Identifier) or not ast.name.startswith("T") or not ast.name[1:].isdigit():
        return None
    return ast.name


def _name_to_generic_type_assignment(name: str) -> ast_.ASTNode:
    return normalize_ast(
        ast_.Assignment(
            ast_.TypedName(
                ast_.Identifier(name),
                ast_.Type_(ast_.Identifier("type"), []),
            ),
            ast_.Identifier("generic"),
            False,
        )
    )


def _unwrap_start_nodes(ast_node: ast_.ASTNode) -> ast_.ASTNode:
    match ast_node:
        case ast_.Start(body, _):
            return _unwrap_start_nodes(body)
        case ast_.Statements([child]):
            return _unwrap_start_nodes(child)
    return ast_node
