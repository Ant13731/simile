from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable, ClassVar, Type, TypeVar


@dataclass
class BaseImplementation:
    """Base class for all Simile implementation libraries.
    Every class represents a Simile object, along with implementations for initialization, cleanup, and operations.
    """

    target: ClassVar[str] = "llvm"
    _numerical_id_counter: ClassVar[int] = 0
    _numerical_id: int = field(init=False)

    def __post_init__(self) -> None:
        self._numerical_id = BaseImplementation._numerical_id_counter
        BaseImplementation._numerical_id_counter += 1

    def create_object(self) -> str:
        """All information needed to create the object should be passed through the class init.
        This function just spits out the generated code to create the object."""
        raise NotImplementedError

    def cleanup_object(self) -> str:
        raise NotImplementedError
