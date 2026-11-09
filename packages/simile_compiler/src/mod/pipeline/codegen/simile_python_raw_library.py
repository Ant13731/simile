from typing import Iterable
from copy import copy


class SimileRuntimeException(Exception):
    pass


class Relation[K, V]:
    # Bi-hashmap implementation of a relation
    def __init__(self) -> None:
        self._fwd: dict[K, list[V]] = {}
        self._bwd: dict[V, list[K]] = {}

    def __iter__(self) -> Iterable[tuple[K, V]]:
        for key, values in self._fwd.items():
            for value in values:
                yield (key, value)

    @classmethod
    def from_dict(cls, d: dict[K, V | list[V]]) -> Relation[K, V]:
        relation = cls()
        for key, value in d.items():
            if isinstance(value, list):
                values: list[V] = value
            else:
                values = [value]

            relation._fwd[key] = values
            for val in values:
                relation._bwd.setdefault(val, []).append(key)
        return relation

    @classmethod
    def from_set_tuple(cls, d: set[tuple[K, V]]) -> Relation[K, V]:
        relation = cls()
        for key, value in d:
            relation.add(key, value)
        return relation

    def add(self, key: K, value: V) -> None:
        self._fwd.setdefault(key, []).append(value)
        self._bwd.setdefault(value, []).append(key)

    def get(self, key: K) -> list[V]:
        return self._fwd.get(key, [])

    def delete_key(self, key: K) -> None:
        if key not in self._fwd:
            return None
        for value in self._fwd[key]:
            self._bwd[value].remove(key)
            if not self._bwd[value]:
                del self._bwd[value]
        del self._fwd[key]

    def delete_value(self, value: V) -> None:
        if value not in self._bwd:
            return None
        for key in self._bwd[value]:
            self._fwd[key].remove(value)
            if not self._fwd[key]:
                del self._fwd[key]
        del self._bwd[value]

    def copy(self: Relation[K, V]) -> Relation[K, V]:
        result: Relation[K, V] = Relation()
        result._fwd = {k: copy(v) for k, v in copy(self._fwd).items()}
        result._bwd = {k: copy(v) for k, v in copy(self._bwd).items()}
        return result

    def inverse(self) -> Relation[V, K]:
        inverse_bimap = Relation[V, K]()
        inverse_bimap._bwd = self._fwd
        inverse_bimap._fwd = self._bwd
        return inverse_bimap

    def compose[T](self: Relation[K, V], other: Relation[V, T]) -> Relation[K, T]:
        result: Relation[K, T] = Relation()
        for self_k in self._fwd:
            for self_v in self._fwd[self_k]:
                if self_v in other._fwd:
                    for other_v in other._fwd[self_v]:
                        result.add(self_k, other_v)
        return result

    def override(self: Relation[K, V], other: Relation[K, V]) -> Relation[K, V]:
        result: Relation[K, V] = self.copy()
        for other_k in other._fwd:
            result._fwd[other_k] = copy(other._fwd[other_k])
            for other_v in other._fwd[other_k]:
                result._bwd.setdefault(other_v, []).append(other_k)
        return result

    @classmethod
    def cartesian_product(cls, v1: Iterable[K], v2: Iterable[V]) -> Relation[K, V]:
        r = Relation[K, V]()
        for x in v1:
            for y in v2:
                r.add(x, y)
        return r

    def domain_subtraction(self: Relation[K, V], other: Iterable[K]) -> Relation[K, V]:
        result: Relation[K, V] = self.copy()
        for v in other:
            result.delete_key(v)
        return result

    def domain_restriction(self: Relation[K, V], other: Iterable[K]) -> Relation[K, V]:
        result: Relation[K, V] = self.copy()
        for v in self._fwd:
            if v not in other:
                result.delete_key(v)
        return result

    def range_subtraction(self: Relation[K, V], other: Iterable[V]) -> Relation[K, V]:
        result: Relation[K, V] = self.copy()
        for v in other:
            result.delete_value(v)
        return result

    def range_restriction(self: Relation[K, V], other: Iterable[V]) -> Relation[K, V]:
        result: Relation[K, V] = self.copy()
        for v in self._bwd:
            if v not in other:
                result.delete_value(v)
        return result

    # TODO union, intersection, set difference


def relation_generator[T1, T2](r1: Iterable[T1], r2: Iterable[T2]) -> Iterable[tuple[T1, T2]]:
    for item1 in r1:
        for item2 in r2:
            yield (item1, item2)


def and_(vs: Iterable[bool]) -> bool:
    ret = True
    exception_thrown = []
    for v in vs:
        if ret is False:
            return False

        try:
            ret = ret and v
        except Exception as e:
            exception_thrown.append(e)
    # Optimistic short-circuiting booleans: only throw an exception
    # if the result is the identity and we have seen an exception
    # If the result is the zero of the boolean, pretend like everything is fine
    if exception_thrown and ret is True:
        raise SimileRuntimeException(exception_thrown)
    return ret


def or_(vs: Iterable[bool]) -> bool:
    ret = False
    exception_thrown = []
    for v in vs:
        if ret is True:
            return True

        try:
            ret = ret or v
        except Exception as e:
            exception_thrown.append(e)
    # Optimistic short-circuiting booleans: only throw an exception
    # if the result is the identity and we have seen an exception
    # If the result is the zero of the boolean, pretend like everything is fine
    if exception_thrown and ret is False:
        raise SimileRuntimeException(exception_thrown)
    return ret


def not_(v: bool) -> bool:
    return not v


def negative(v: int | float) -> int | float:
    return -v


def inverse(r: Relation) -> Relation:
    return r.inverse()


def implies(b1: bool, b2: bool) -> bool:
    return not b1 or b2


def add(v1, v2):
    return v1 + v2


def subtract(v1, v2):
    return v1 - v2


def multiply(v1, v2):
    return v1 * v2


def divide(v1, v2):
    return v1 / v2


def int_divide(v1, v2):
    return v1 // v2


def modulo(v1, v2):
    return v1 % v2


def exponent(v1, v2):
    return v1**v2


def less_than(v1, v2):
    return v1 < v2


def less_than_or_equal(v1, v2):
    return v1 <= v2


def greater_than(v1, v2):
    return v1 > v2


def greater_than_or_equal(v1, v2):
    return v1 >= v2


def equal(v1, v2):
    return v1 == v2


def not_equal(v1, v2):
    return v1 != v2


def in_(v1, v2):
    return v1 in v2


def not_in(v1, v2):
    return v1 not in v2


def union(v1, v2):
    return v1 | v2


def intersection(v1, v2):
    return v1 & v2


def difference(v1, v2):
    return v1 - v2


def subset(v1, v2):
    return v1 < v2


def subset_eq(v1, v2):
    return v1 <= v2


def superset(v1, v2):
    return v1 > v2


def superset_eq(v1, v2):
    return v1 >= v2


def not_subset(v1, v2):
    return not subset(v1, v2)


def not_subset_eq(v1, v2):
    return not subset_eq(v1, v2)


def not_superset(v1, v2):
    return not superset(v1, v2)


def not_superset_eq(v1, v2):
    return not superset_eq(v1, v2)


def maplet(v1, v2):
    return (v1, v2)


def relation_overriding(v1: Relation, v2):
    return v1.override(v2)


def composition(v1: Relation, v2):
    return v1.compose(v2)


def cartesian_product(v1, v2):
    r = Relation()
    for x in v1:
        for y in v2:
            r.add(x, y)
    return r


def upto(v1, v2):
    return set(range(v1, v2 + 1))


def domain_subtraction(v1: Relation, v2):
    return v1.domain_subtraction(v2)


def domain_restriction(v1: Relation, v2):
    return v1.domain_restriction(v2)


def range_subtraction(v1: Relation, v2):
    return v1.range_subtraction(v2)


def range_restriction(v1: Relation, v2):
    return v1.range_restriction(v2)


def concat(v1, v2):
    return v1 + v2
