"""Parser-only AST nodes. These do not hold types or other analysis information.
These types will be replaced by typed ASTs will be used after type analysis"""

from dataclasses import dataclass
from typing import Generic, TypeVar

from src.mod.data.ast_.symbol_table_types import SimileType, DeferToSymbolTable, PairType, TupleType
from src.mod.data.ast_.base import ASTNode


@dataclass
class Identifier(ASTNode):
    """Identifier for variables, functions, etc. in the AST."""

    name: str

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Identifier):
            return False
        return self.name == other.name

    @property
    def free(self) -> set[Identifier]:
        return {self}

    def _get_type(self) -> SimileType:
        if self._env is not None:
            ret = self._env.get(self.name)
            if ret is not None:
                return ret
        return DeferToSymbolTable(lookup_type=self.name)

    def flatten(self) -> set[Identifier]:
        """Used to simplify the flatten operation of :cls:`MapletIdentifier`"""
        return {self}


@dataclass
class TupleIdentifier(ASTNode):
    """Special variation of tuple used for binding loop and quantification variables (also hashable)"""

    items: tuple[IdentifierListTypes, ...]

    def __hash__(self) -> int:
        return hash(self.items)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TupleIdentifier):
            return False
        return self.items == other.items

    @property
    def free(self) -> set[Identifier]:
        return self.flatten()

    def well_formed(self) -> bool:
        identifiers = list(self.flatten())
        for i in range(len(identifiers)):
            for j in range(i + 1, len(identifiers)):
                if identifiers[i] == identifiers[j]:
                    return False
        return True

    def _get_type(self) -> SimileType:
        return TupleType(tuple(map(lambda x: x.get_type, self.items)))

    def flatten(self) -> set[Identifier]:
        flat_set = set()
        for item in self.items:
            flat_set |= item.flatten()
        return flat_set

    def flatten_until_leaf_node(self) -> list[Identifier | MapletIdentifier]:
        ret: list[Identifier | MapletIdentifier] = []
        for item in self.items:
            if isinstance(item, MapletIdentifier):
                ret.append(item)
            elif isinstance(item, TupleIdentifier):
                ret.extend(item.flatten_until_leaf_node())
            else:
                ret.append(item)
        return ret

    @classmethod
    def from_maplet(cls, left: IdentifierListTypes, right: IdentifierListTypes):
        return cls((left, right))


L = TypeVar("L", bound="Identifier | TupleIdentifier | MapletIdentifier")
R = TypeVar("R", bound="Identifier | TupleIdentifier | MapletIdentifier")


@dataclass
class MapletIdentifier(TupleIdentifier, Generic[L, R]):
    """Special variation of maplet used for binding loop and quantification variables (also hashable)"""

    def __init__(self, left: L | tuple[IdentifierListTypes], right: R | None = None) -> None:
        if isinstance(left, tuple):
            assert right is None, "If left is a tuple, right must be None"
            super().__init__(left)
        else:
            assert right is not None, "If left is not a tuple, right must be provided"
            super().__init__((left, right))

    @property
    def left(self) -> L:
        # python cant handle generic tuples just yet, so just ignore the type checker here
        return self.items[0]  # type: ignore

    @left.setter
    def left(self, value: L) -> None:
        self.items = (value, self.items[1])

    @property
    def right(self) -> R:
        return self.items[1]  # type: ignore

    @right.setter
    def right(self, value: R) -> None:
        self.items = (self.items[0], value)

    def __hash__(self) -> int:
        return hash((self.left, self.right))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MapletIdentifier):
            return False
        return self.left == other.left and self.right == other.right

    @property
    def free(self) -> set[Identifier]:
        return self.flatten()

    def _get_type(self) -> SimileType:
        return PairType(self.left.get_type, self.right.get_type)

    def flatten(self) -> set[Identifier]:
        return self.left.flatten() | self.right.flatten()


IdentifierListTypes = Identifier | MapletIdentifier | TupleIdentifier
