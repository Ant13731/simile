from __future__ import annotations
from dataclasses import dataclass

from src.mod.data.implementations.interfaces.base import BaseImplementation


@dataclass
class BoolImplementation(BaseImplementation):

    def not_(self) -> BoolImplementation:
        raise NotImplementedError

    def equivalent(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def not_equivalent(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def implies(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def and_(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def or_(self, other: BaseImplementation) -> str:
        raise NotImplementedError


@dataclass
class NoneImplementation(BaseImplementation):
    """Intended for statements without a type, not expressions. For example, a while loop node doesn't have a type."""


@dataclass
class StringImplementation(BaseImplementation):
    pass


@dataclass
class IntImplementation(BaseImplementation):

    # Comparison
    def greater_than(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def less_than(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def greater_than_equals(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def less_than_equals(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    # Arithmetic
    def negate(self) -> str:
        raise NotImplementedError

    def int_division(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def modulo(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def add(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def subtract(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def division(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def multiply(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def power(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    # Sets
    def upto(self, other: IntImplementation) -> str:
        raise NotImplementedError


@dataclass
class FloatImplementation(BaseImplementation):

    def greater_than(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def less_than(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def greater_than_equals(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def less_than_equals(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def negate(self) -> str:
        raise NotImplementedError

    def add(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def subtract(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def division(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def multiply(self, other: BaseImplementation) -> str:
        raise NotImplementedError

    def power(self, other: BaseImplementation) -> str:
        raise NotImplementedError
