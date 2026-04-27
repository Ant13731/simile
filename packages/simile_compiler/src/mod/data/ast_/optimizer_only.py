from __future__ import annotations
from dataclasses import dataclass, field

from src.mod.data.ast_.base import ASTNode
from src.mod.data.ast_.common_extended import (
    In,
    And,
    Or,
)
from src.mod.data.ast_.parser_only import Identifier, MapletIdentifier
from src.mod.data.ast_.symbol_table_types import SimileType, BaseSimileType


@dataclass
class GeneratorSelection(ASTNode):
    generators: list[In]
    predicates: And

    def flatten(self) -> And:
        ret: list[ASTNode] = []
        ret += self.generators
        ret += self.predicates.items
        return And(ret)

    @property
    def bound_identifiers(self) -> set[Identifier | MapletIdentifier]:
        bound_identifiers = set()
        for generator in self.generators:
            assert isinstance(generator.left, Identifier | MapletIdentifier), f"Expected Identifier or MapletIdentifier, got {type(generator.left)}"
            if generator.left in bound_identifiers:
                raise ValueError(f"Identifier {generator.left} is already bound in the generator selection. All generators are expected to bind unique identifiers")

            bound_identifiers.add(generator.left)
        return bound_identifiers

    def _get_type(self) -> SimileType:
        return self.flatten()._get_type()


@dataclass
class CombinedGeneratorSelection(ASTNode):
    generator: In
    gsp_predicates: Or  # Or[GeneratorSelectionV2 | Bool] # Bool here is for empty gsp
    predicates: And = field(default_factory=lambda: And([]))

    def flatten(self) -> And:
        ret: list[ASTNode] = [self.generator]
        ret.append(self.gsp_predicates)
        ret += self.predicates.items
        return And(ret)

    @property
    def bound_identifier(self) -> Identifier | MapletIdentifier:
        assert isinstance(self.generator.left, Identifier | MapletIdentifier), f"Expected Identifier or MapletIdentifier, got {type(self.generator.left)}"
        return self.generator.left

    def _get_type(self) -> SimileType:
        return self.flatten()._get_type()


@dataclass
class SingleGeneratorSelection(ASTNode):
    generator: In
    predicates: And

    def flatten(self) -> And:
        ret = [self.generator] + self.predicates.items
        return And(ret)

    @property
    def bound_identifier(self) -> Identifier | MapletIdentifier:
        assert isinstance(self.generator.left, Identifier | MapletIdentifier), f"Expected Identifier or MapletIdentifier, got {type(self.generator.left)}"
        return self.generator.left

    def _get_type(self) -> SimileType:
        return self.flatten()._get_type()


@dataclass
class Loop(ASTNode):
    predicate: Or | GeneratorSelection | CombinedGeneratorSelection | SingleGeneratorSelection
    body: ASTNode

    def _get_type(self) -> SimileType:
        return BaseSimileType.None_
