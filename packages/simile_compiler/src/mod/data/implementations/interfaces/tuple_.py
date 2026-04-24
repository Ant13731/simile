from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable

from src.mod.data.implementations.interfaces.base import BaseImplementation


@dataclass
class TupleImplementation(BaseImplementation):

    @classmethod
    def enumeration(cls, element_types: list[BaseImplementation]) -> str:
        raise NotImplementedError


@dataclass
class PairImplementation(BaseImplementation):

    @classmethod
    def maplet(cls, key_type: BaseImplementation, value_type: BaseImplementation) -> str:
        raise NotImplementedError
