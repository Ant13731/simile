from __future__ import annotations
from dataclasses import dataclass

from src.mod.data.implementations.interfaces.base import BaseImplementation


@dataclass
class ModuleImportsImplementation(BaseImplementation):
    """Type to represent importing these objects into the module namespace

    Any type-checking functions called on environments (which is what this dict really is) should raise an error."""

    import_objects: dict[str, BaseImplementation]
