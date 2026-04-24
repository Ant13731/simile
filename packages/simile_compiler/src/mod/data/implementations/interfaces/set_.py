from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable, TypeVar, Type

from src.mod.data.implementations.interfaces.base import BaseImplementation


@dataclass
class SetImplementation(BaseImplementation):
    # Programming-oriented operations
    def copy(self) -> str:
        raise NotImplementedError

    def clear(self) -> str:
        raise NotImplementedError

    def is_empty(self) -> str:
        raise NotImplementedError

    # Atomic operations
    def add(self, element: BaseImplementation) -> str:
        raise NotImplementedError

    def remove(self, element: BaseImplementation) -> str:
        raise NotImplementedError

    def in_(self, element: BaseImplementation) -> str:
        raise NotImplementedError

    def not_in(self, element: BaseImplementation) -> str:
        raise NotImplementedError

    @classmethod
    def enumeration(cls, element_implementations: list[BaseImplementation]) -> str:
        raise NotImplementedError

    # Single operations
    def cardinality(self) -> str:
        raise NotImplementedError

    def powerset(self) -> str:
        raise NotImplementedError

    def map(self, func: BaseImplementation) -> str:
        raise NotImplementedError

    def choice(self) -> str:
        raise NotImplementedError

    def sum(self) -> str:
        raise NotImplementedError

    def product(self) -> str:
        raise NotImplementedError

    def min(self) -> str:
        raise NotImplementedError

    def max(self) -> str:
        raise NotImplementedError

    def map_min(self, func: BaseImplementation) -> str:
        raise NotImplementedError

    def map_max(self, func: BaseImplementation) -> str:
        raise NotImplementedError

    # Binary operations
    def union(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def intersection(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def difference(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def symmetric_difference(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def cartesian_product(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def is_disjoint(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def is_subset(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def is_subset_equals(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def is_superset(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def is_superset_equals(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def not_is_subset(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def not_is_subset_equals(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def not_is_superset(self, other: SetImplementation) -> str:
        raise NotImplementedError

    def not_is_superset_equals(self, other: SetImplementation) -> str:
        raise NotImplementedError


@dataclass
class RelationImplementation(SetImplementation):

    def inverse(self) -> str:
        raise NotImplementedError

    def composition(self, other: RelationImplementation) -> str:
        raise NotImplementedError

    def function_call(self, argument: BaseImplementation) -> str:
        raise NotImplementedError

    def image(self, argument: BaseImplementation) -> str:
        raise NotImplementedError

    def overriding(self, other: RelationImplementation) -> str:
        raise NotImplementedError

    def domain(self) -> str:
        raise NotImplementedError

    def range_(self) -> str:
        raise NotImplementedError

    def domain_restriction(self, domain_set: SetImplementation) -> str:
        raise NotImplementedError

    def domain_subtraction(self, domain_set: SetImplementation) -> str:
        raise NotImplementedError

    def range_restriction(self, range_set: SetImplementation) -> str:
        raise NotImplementedError

    def range_subtraction(self, range_set: SetImplementation) -> str:
        raise NotImplementedError

    def bag_image(self, bag: BagImplementation) -> str:
        raise NotImplementedError


@dataclass
class BagImplementation(RelationImplementation):

    def bag_union(self, other: BagImplementation) -> str:
        raise NotImplementedError

    def bag_intersection(self, other: BagImplementation) -> str:
        raise NotImplementedError

    def bag_add(self, other: BagImplementation) -> str:
        raise NotImplementedError

    def bag_difference(self, other: BagImplementation) -> str:
        raise NotImplementedError

    def size(self) -> str:
        raise NotImplementedError


@dataclass
class SequenceImplementation(RelationImplementation):

    def concat(self, other: SequenceImplementation) -> str:
        raise NotImplementedError
