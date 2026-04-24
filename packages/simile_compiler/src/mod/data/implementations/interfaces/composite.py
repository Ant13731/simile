from __future__ import annotations
from dataclasses import dataclass, field
from collections import OrderedDict

from src.mod.data.implementations.interfaces.base import BaseImplementation


@dataclass
class RecordImplementation(BaseImplementation):
    def access(self, field_name: str) -> str:
        raise NotImplementedError


@dataclass
class EnumImplementation(BaseImplementation):
    pass


@dataclass
class ProcedureImplementation(BaseImplementation):
    def call(self, arg_types: list[BaseImplementation]) -> BaseImplementation:
        raise NotImplementedError
