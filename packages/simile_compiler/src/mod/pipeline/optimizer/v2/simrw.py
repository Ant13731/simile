from __future__ import annotations
from typing import Any, Callable, Sequence, ClassVar
from dataclasses import dataclass, field
from copy import deepcopy

from loguru import logger

from src.mod.data import ast_, traits, types
from src.mod.data.helpers.dataclass import dataclass_traverse
from src.mod.pipeline.analysis import TypeAnnotationResolver, make_symbol_table
from src.mod.pipeline.analysis.trait_resolver import TraitResolver
from src.mod.pipeline.analysis.type_synthesizer import TypeSynthesizer
from src.mod.pipeline.parser import parse
from src.mod.pipeline.optimizer.v2.simrw_parser import SimrwAST
from src.mod.pipeline.optimizer.v2.structure_matcher import StructureMatcher
from src.mod.pipeline.optimizer.v2.guard_condition import PatternMatchVars, GuardCondition, GUARD_CONDITIONS
from src.mod.pipeline.printers.ast_ import ast_to_source


@dataclass
class RewriteRule:
    name: str
    vars_: PatternMatchVars
    rewrite_left: ast_.ASTNode
    rewrite_right: ast_.ASTNode
    # These should be guarding functions that accept vars_
    when: list[GuardCondition]


def apply_rewrite_rule(rule: RewriteRule, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
    logger.debug(f"Applying rewrite rule {rule.name} to AST: {ast_to_source(ast)}")
    result = ast.find_and_replace_with_func(lambda node: _apply_rewrite_rule(rule, node, type_synthesizer))
    logger.debug(f"Rewrite rule result: {ast_to_source(result)}")
    return result


def _apply_rewrite_rule(rule: RewriteRule, ast: ast_.ASTNode, type_synthesizer: TypeSynthesizer) -> ast_.ASTNode | None:
    # Attempt to structurally pattern match with the LH side
    # Collect the substituted vars in a dict for reversal later - assign a str to part of the AST
    structure_matcher = StructureMatcher(set(rule.vars_.keys()))
    substitutions = structure_matcher.match(ast, rule.rewrite_left)
    if not substitutions:
        logger.debug("Failed to match: couldn't find substitutions")
        return None

    # Check against typed vars (ast types should be a subset of the rewrite types)
    for name, matched_ast in substitutions.items():
        matched_ast_type = type_synthesizer.synthesize_type(matched_ast)
        expected_var_type = rule.vars_[name]
        if not matched_ast_type.is_subtype(expected_var_type):
            logger.debug("Failed to match: matched AST type is not a subtype of expected var type")
            return None

    # Check guard conditions
    for guard_condition in rule.when:
        if not guard_condition.guard(ast, rule.vars_):
            logger.debug(f"Failed to match: guard condition {guard_condition.name}")
            return None

    # Apply the right hand structural match
    # Substitute vars
    replacement_ast = deepcopy(rule.rewrite_right)
    for name, matched_ast in substitutions.items():
        replacement_ast = replacement_ast.find_and_replace(ast_.Identifier(name), matched_ast)
    logger.debug(f"Rewrite rule {rule.name} applied successfully")
    return replacement_ast


def convert_simrw_to_rewrite_rules(rewrite_rule_asts: list[SimrwAST]) -> list[RewriteRule]:
    rewrite_rules: list[RewriteRule] = []
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

        rewrite_rule = RewriteRule(
            name=rewrite_rule_ast.name,
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
    if isinstance(var_ast_combined.body, ast_.None_):
        return {}
    var_asts = var_ast_combined.body.items

    ast_vars: dict[str, ast_.ASTNode] = {}
    ast_var_traits: dict[str, traits.Traits | None] = {}
    trait_only_base_symbol_table = make_symbol_table(ast_.Statements([]))
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
        # Unwrap and collect LH variable identifiers
        ast_vars[var_ast.name.name] = var_ast
        ast_var_traits[var_ast.name.name] = trait_collection

    # Search types for identifiers of the form T[0-9]*. These identifiers are reserved for generic types
    # If one of the LH var identifiers matches T[0-9]*, throw an error (and suggest that any variable names use T_... instead)
    for var_name in ast_vars:
        if var_name.startswith("T") and var_name[1:].isdigit():
            raise ValueError(f"Variable names matching T[0-9]* (like '{var_name}') are reserved for (implicit) generic types. Please use a different name (e.g., T_...).")

    generic_type_assignments: list[ast_.ASTNode] = []
    for typed_name_ast in ast_vars.values():
        implicitly_defined_generic_type_names = list(filter(None, dataclass_traverse(typed_name_ast, _is_implicitly_defined_generic_type)))
        generic_type_assignments.extend(list(map(_name_to_generic_type_assignment, implicitly_defined_generic_type_names)))

    # Add required generic types to the symbol table (all other types are expected to be builtins)
    generic_symbol_table = make_symbol_table(ast_.Statements(generic_type_assignments))
    # Synthesize types for each var identifier (remember to handle traits)
    typed_vars: dict[str, types.BaseType] = {}
    for var_name, typed_name_ast in ast_vars.items():
        trait_collection = ast_var_traits.get(var_name)
        var_type = TypeAnnotationResolver.resolve_type_annotation(typed_name_ast, generic_symbol_table)
        if trait_collection:
            var_type.traits = var_type.traits.merge_copy(trait_collection)
        typed_vars[var_name] = var_type

    return typed_vars


def _is_implicitly_defined_generic_type(ast: Any) -> str | None:
    if not isinstance(ast, ast_.Identifier) or not ast.name.startswith("T") or not ast.name[1:].isdigit():
        return None
    return ast.name


def _name_to_generic_type_assignment(name: str) -> ast_.ASTNode:
    return ast_.Assignment(
        ast_.TypedName(
            ast_.Identifier(name),
            ast_.Type_(ast_.Identifier("type"), []),
        ),
        ast_.Identifier("generic"),
        False,
    )


def _unwrap_start_nodes(ast_node: ast_.ASTNode) -> ast_.ASTNode:
    match ast_node:
        case ast_.Start(body, _):
            return _unwrap_start_nodes(body)
        case ast_.Statements([child]):
            return _unwrap_start_nodes(child)
    return ast_node
