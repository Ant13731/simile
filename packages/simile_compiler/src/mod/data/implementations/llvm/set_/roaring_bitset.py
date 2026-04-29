from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable, TypeVar, Type

from src.mod.data.implementations.interfaces.base import BaseImplementation
from src.mod.data.implementations.interfaces.set_ import SetImplementation


@dataclass
class RoaringBitsetImplementation(SetImplementation):

    def create_object(self) -> str:
        raise NotImplementedError

    def cleanup_object(self) -> str:
        raise NotImplementedError

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
