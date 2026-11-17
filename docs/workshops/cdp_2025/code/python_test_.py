from __future__ import annotations
from typing import Self, Any
import random
import timeit

import csv
import tracemalloc

PERSON_TO_WORKSHOP_RATIO = 5
TEST_RUNS = 15
REPEAT_RUNS = 10


# Class credit: https://stackoverflow.com/questions/3318625/how-to-implement-an-efficient-bidirectional-hash-table
# class BiHashMap[K, V](dict[K, list[V]]):
#     def __init__(self, *args, **kwargs) -> None:
#         super().__init__(*args, **kwargs)
#         self._inverse: dict[V, list[K]] = {}

#         for key, value in self.items():
#             for val in value if isinstance(value, list) else [value]:
#                 self._inverse.setdefault(val, []).append(key)

#     def inverse(self) -> BiHashMap[V, K]:
#         inverse_bimap = BiHashMap[V, K]()
#         inverse_bimap._inverse = self
#         for val, keys in self._inverse.items():
#             inverse_bimap[val] = keys
#         return inverse_bimap

#     def __setitem__(self, key, value):
#         if key in self:
#             for v in self[key]:
#                 self._inverse[v].remove(key)
#         super().__setitem__(key, value)
#         for val in value if isinstance(value, list) else [value]:
#             self._inverse.setdefault(val, []).append(key)

#     def __delitem__(self, key):
#         for v in self[key]:
#             self._inverse.setdefault(v, []).remove(key)

#         for v in self[key]:
#             if v in self._inverse and not self._inverse[v]:
#                 del self._inverse[v]

#         super().__delitem__(key)


class TestInterface:
    output_file_runtime: str
    output_file_memory: str

    @staticmethod
    def make_test_inputs(size: int) -> tuple[TestInterface, TestInterface, int]:
        raise NotImplementedError

    @staticmethod
    def get_num_meals(location: Any, attends: Any, room: int) -> int:
        raise NotImplementedError


class BiHashMap[K, V](TestInterface):
    output_file_runtime = "benchmark_runtime_python_bihashmap.csv"
    output_file_memory = "benchmark_memory_python_bihashmap.csv"

    def __init__(self, *, from_dict: dict[K, V] | None = None) -> None:
        self._fwd: dict[K, list[V]] = {}
        self._bwd: dict[V, list[K]] = {}

        if from_dict:
            self._fwd = {key: [value] for key, value in from_dict.items()}
            for key, value in from_dict.items():
                for val in value if isinstance(value, list) else [value]:
                    self._bwd.setdefault(val, []).append(key)

    def add(self, key: K, value: V) -> None:
        self._fwd.setdefault(key, []).append(value)
        self._bwd.setdefault(value, []).append(key)

    def get(self, key: K) -> list[V]:
        return self._fwd.get(key, [])

    def inverse(self) -> BiHashMap[V, K]:
        inverse_bimap = BiHashMap[V, K]()
        inverse_bimap._bwd = self._fwd
        inverse_bimap._fwd = self._bwd
        return inverse_bimap

    def compose[T](self: BiHashMap[K, V], other: BiHashMap[V, T]) -> BiHashMap[K, T]:
        result: BiHashMap[K, T] = BiHashMap()
        for self_k in self._fwd:
            for self_v in self._fwd[self_k]:
                if self_v in other._fwd:
                    for other_v in other._fwd[self_v]:
                        result.add(self_k, other_v)
        return result

    @staticmethod
    def make_test_inputs(size: int) -> tuple[BiHashMap[str, int], BiHashMap[str, str], int]:
        workshops = [f"Workshop{i}" for i in range(size)]
        people = list(set([f"Person{i}" for i in range(size * PERSON_TO_WORKSHOP_RATIO)]))

        location: BiHashMap[str, int] = BiHashMap()
        attends: BiHashMap[str, str] = BiHashMap()
        room = random.randint(1, size - 1)

        for i in range(size):
            location.add(workshops[i], i)

        for i in range(size * PERSON_TO_WORKSHOP_RATIO):
            attends.add(people[i], random.choice(workshops))

        return location, attends, room

    @staticmethod
    def get_num_meals(location: BiHashMap[str, int], attends: BiHashMap[str, str], room: int) -> int:
        return len(location.inverse().compose(attends.inverse()).get(room))


class BiMapTupleSet[K, V](TestInterface):
    output_file_runtime = "benchmark_runtime_python_bimap_tuple.csv"
    output_file_memory = "benchmark_memory_python_bimap_tuple.csv"

    def __init__(self, *, from_set: set[tuple[K, V]] | None = None, from_dict: dict[K, V] | None = None) -> None:
        if from_dict:
            self.bimap: set[tuple[K, V]] = set(from_dict.items())
        elif from_set:
            self.bimap = from_set
        else:
            self.bimap = set()

    def inverse(self) -> BiMapTupleSet[V, K]:
        return BiMapTupleSet(from_set={(v, k) for (k, v) in self.bimap})

    def add(self, k: K, v: V) -> None:
        self.bimap.add((k, v))

    def get(self, key: K) -> list[V]:
        return [v for k, v in self.bimap if k == key]

    def compose[T](self, other: BiMapTupleSet[V, T]) -> BiMapTupleSet[K, T]:
        result: BiMapTupleSet[K, T] = BiMapTupleSet()
        for k, v in self.bimap:
            for v2, t in other.bimap:
                if v == v2:
                    result.bimap.add((k, t))
        return result

    @staticmethod
    def make_test_inputs(size: int) -> tuple[BiMapTupleSet[str, int], BiMapTupleSet[str, str], int]:
        workshops = [f"Workshop{i}" for i in range(size)]
        people = list(set([f"Person{i}" for i in range(size * PERSON_TO_WORKSHOP_RATIO)]))

        location: BiMapTupleSet[str, int] = BiMapTupleSet()
        attends: BiMapTupleSet[str, str] = BiMapTupleSet()
        room = random.randint(1, size - 1)

        for i in range(size):
            location.add(workshops[i], i)

        for i in range(size * PERSON_TO_WORKSHOP_RATIO):
            attends.add(people[i], random.choice(workshops))

        return location, attends, room

    @staticmethod
    def get_num_meals(location: BiMapTupleSet[str, int], attends: BiMapTupleSet[str, str], room: int) -> int:
        return len(location.inverse().compose(attends.inverse()).get(room))


class FunctionalRelationDict[K, V](dict[K, V], TestInterface):
    output_file_runtime = "benchmark_runtime_python_optimized_dict.csv"
    output_file_memory = "benchmark_memory_python_optimized_dict.csv"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def make_test_inputs(size: int) -> tuple[FunctionalRelationDict[str, int], FunctionalRelationDict[str, str], int]:
        workshops = [f"Workshop{i}" for i in range(size)]
        people = list(set([f"Person{i}" for i in range(size * PERSON_TO_WORKSHOP_RATIO)]))

        location: FunctionalRelationDict[str, int] = FunctionalRelationDict()
        attends: FunctionalRelationDict[str, str] = FunctionalRelationDict()
        room = random.randint(1, size - 1)

        for i in range(size):
            location[workshops[i]] = i

        for i in range(size * PERSON_TO_WORKSHOP_RATIO):
            attends[people[i]] = random.choice(workshops)

        return location, attends, room

    @staticmethod
    def get_num_meals(location: dict[str, int], attends: dict[str, str], room: int) -> int:
        num_meals = 0
        for _, workshop in attends.items():
            if location.get(workshop) == room:
                num_meals += 1
        return num_meals


def test_runtime(cls: type[TestInterface]) -> None:
    print(f"Testing runtime for {cls.__name__}")
    with open(f"results/{cls.output_file_runtime}", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=",")

        for i in range(2, TEST_RUNS):
            inputs = cls.make_test_inputs(2**i)
            test_time = timeit.timeit(lambda: cls.get_num_meals(*inputs), number=REPEAT_RUNS)
            csvwriter.writerow([2**i, test_time])
            print(f"{2**i},", test_time)


def test_memory(cls: type[TestInterface]) -> None:
    print(f"Testing memory for {cls.__name__}")
    tracemalloc.start()
    with open(f"results/{cls.output_file_memory}", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=",")

        for i in range(2, TEST_RUNS):
            inputs = cls.make_test_inputs(2**i)
            tracemalloc.reset_peak()
            res = cls.get_num_meals(*inputs)
            current, peak = tracemalloc.get_traced_memory()
            csvwriter.writerow([2**i, peak])
            print(f"{2**i},", peak)


def main():

    # print(FunctionalRelationDict.get_num_meals(*FunctionalRelationDict.make_test_inputs(10)))

    test_runtime(BiHashMap)
    test_runtime(BiMapTupleSet)
    test_runtime(FunctionalRelationDict)
    test_memory(BiHashMap)
    test_memory(BiMapTupleSet)
    test_memory(FunctionalRelationDict)


if __name__ == "__main__":
    main()
