from __future__ import annotations
from dataclasses import dataclass, field

from src.mod.data import ast_


@dataclass
class GeneratorSelection(ast_.ASTNode):
    generators: list[ast_.In]
    predicates: ast_.And

    def flatten(self) -> ast_.And:
        ret: list[ast_.ASTNode] = []
        ret += self.generators
        ret += self.predicates.items
        return ast_.And(ret)

    @property
    def bound_identifiers(self) -> set[ast_.Identifier | ast_.MapletIdentifier]:
        bound_identifiers = set()
        for generator in self.generators:
            assert isinstance(generator.left, ast_.Identifier | ast_.MapletIdentifier), f"Expected Identifier or MapletIdentifier, got {type(generator.left)}"
            if generator.left in bound_identifiers:
                raise ValueError(f"Identifier {generator.left} is already bound in the generator selection. All generators are expected to bind unique identifiers")

            bound_identifiers.add(generator.left)
        return bound_identifiers

    def _get_type(self) -> ast_.SimileType:
        return self.flatten()._get_type()


@dataclass
class CombinedGeneratorSelection(ast_.ASTNode):
    generator: ast_.In
    gsp_predicates: ast_.Or  # Or[GeneratorSelectionV2 | Bool] # Bool here is for empty gsp
    predicates: ast_.And = field(default_factory=lambda: ast_.And([]))

    def flatten(self) -> ast_.And:
        ret: list[ast_.ASTNode] = [self.generator]
        ret.append(self.gsp_predicates)
        ret += self.predicates.items
        return ast_.And(ret)

    @property
    def bound_identifier(self) -> ast_.Identifier | ast_.MapletIdentifier:
        assert isinstance(self.generator.left, ast_.Identifier | ast_.MapletIdentifier), f"Expected Identifier or MapletIdentifier, got {type(self.generator.left)}"
        return self.generator.left

    def _get_type(self) -> ast_.SimileType:
        return self.flatten()._get_type()


@dataclass
class SingleGeneratorSelection(ast_.ASTNode):
    generator: ast_.In
    predicates: ast_.And

    def flatten(self) -> ast_.And:
        ret = [self.generator] + self.predicates.items
        return ast_.And(ret)

    @property
    def bound_identifier(self) -> ast_.Identifier | ast_.MapletIdentifier:
        assert isinstance(self.generator.left, ast_.Identifier | ast_.MapletIdentifier), f"Expected Identifier or MapletIdentifier, got {type(self.generator.left)}"
        return self.generator.left

    def _get_type(self) -> ast_.SimileType:
        return self.flatten()._get_type()


@dataclass
class Loop(ast_.ASTNode):
    predicate: ast_.Or | GeneratorSelection | CombinedGeneratorSelection | SingleGeneratorSelection
    body: ast_.ASTNode

    def _get_type(self) -> ast_.SimileType:
        return ast_.BaseSimileType.None_
