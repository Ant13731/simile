from dataclasses import fields, is_dataclass
from typing import TypeVar, Callable, Any, Iterable

T = TypeVar("T")
V = TypeVar("V")


def dataclass_children(
    traversal_target: Any,
) -> list[Any]:
    """Return all children of a dataclass instance."""
    if not is_dataclass(traversal_target):
        return []
    children = []
    for f in fields(traversal_target):
        field_value = getattr(traversal_target, f.name)
        if isinstance(field_value, list):
            for item in field_value:
                children.append(item)
        else:
            children.append(field_value)
    return children


def dataclass_traverse(
    traversal_target: Any,
    visit: Callable[[Any], T],
    visit_leaves: bool = False,
    visit_root: bool = True,
) -> list[T]:
    """Apply a visit function to all dataclass instances in the traversal target (pre-order traversal, root node first), accumulating results.

    Args:
        traversal_target: The target to traverse.
        visit: A function to apply to each dataclass instance.
        visit_leaves: Whether to visit and accumulate on leaf (non-dataclass) nodes. Defaults to False.
        visit_root: Whether to visit the root node. Defaults to True.

    Returns:
        list[T]: A list of results from the visit function.
    """

    accumulator: list[T] = []
    _dataclass_traverse_helper(
        traversal_target,
        visit,
        accumulator,
        visit_leaves,
        visit_root,
    )
    return accumulator


def _dataclass_traverse_helper(
    traversal_target: Any,
    visit: Callable[[Any], T],
    accumulator: list[T],
    visit_leaves: bool,
    visit_root: bool,
) -> None:
    assert is_dataclass(traversal_target), "Traversal techniques only work with the dataclass `fields` function"
    if visit_root:
        accumulator.append(visit(traversal_target))
    for f in fields(traversal_target):
        field_value = getattr(traversal_target, f.name)
        if isinstance(field_value, list):
            for item in field_value:
                if is_dataclass(item):
                    _dataclass_traverse_helper(
                        item,
                        visit,
                        accumulator,
                        visit_leaves,
                        visit_root,
                    )
        elif is_dataclass(field_value):
            _dataclass_traverse_helper(
                field_value,
                visit,
                accumulator,
                visit_leaves,
                visit_root,
            )
        elif visit_leaves:
            accumulator.append(visit(field_value))


def _dataclass_traverse_helper_2(
    traversal_target: Any,
    visit: Callable[[Any], T],
    accumulator: list[T],
    visit_leaves: bool,
    visit_root: bool,
) -> None:
    assert is_dataclass(traversal_target), "Traversal techniques only work with the dataclass `fields` function"
    if visit_root:
        accumulator.append(visit(traversal_target))
    for f in dataclass_children(traversal_target):
        if is_dataclass(f):
            _dataclass_traverse_helper(
                f,
                visit,
                accumulator,
                visit_leaves,
                visit_root,
            )
        elif visit_leaves:
            accumulator.append(visit(f))


def is_dataclass_leaf(obj: Any) -> bool:
    """Check if the object is a dataclass leaf (i.e., has no dataclass/list of dataclass children)."""
    if not is_dataclass(obj):
        return True
    for f in dataclass_children(obj):
        if is_dataclass(f):
            return False
    return True


def dataclass_find_and_replace(
    traversal_target: Any,
    rewrite_func: Callable[[Any], Any | None],
) -> Any:
    """Find and replace dataclass instances using a rewrite function (post-order, root last)."""
    assert is_dataclass(traversal_target), "Traversal techniques only work with the dataclass `fields` function"

    # Bottom up traversal
    for f in fields(traversal_target):
        field_value = getattr(traversal_target, f.name)
        if isinstance(field_value, list):
            new_list = []
            for item in field_value:
                if is_dataclass(item):
                    new_item = dataclass_find_and_replace(item, rewrite_func)
                    if new_item is not None:
                        new_list.append(new_item)
                else:
                    new_list.append(item)
            setattr(traversal_target, f.name, new_list)
        elif isinstance(field_value, dict):
            new_dict = {}
            for k, v in field_value.items():
                if is_dataclass(v):
                    new_dict[k] = dataclass_find_and_replace(v, rewrite_func)
                else:
                    new_dict[k] = v
            setattr(traversal_target, f.name, new_dict)
        elif is_dataclass(field_value):
            new_value = dataclass_find_and_replace(field_value, rewrite_func)
            setattr(traversal_target, f.name, new_value)

    replacement_target = rewrite_func(traversal_target)
    if replacement_target is not None:
        return replacement_target
    else:
        return traversal_target


def flatten(xss: Iterable[Iterable[T]]) -> list[T]:
    return [x for xs in xss for x in xs]


# def find_and_replace(
#     traversal_target: Any,
#     rewrite_func: Callable[[Any], Any | None],
# ) -> Any:
#     assert is_dataclass(traversal_target), "Traversal techniques only work with the dataclass `fields` function"
#     # Bottom up traversal
#     for f in fields(traversal_target):
#         field_value = getattr(traversal_target, f.name)
#         if isinstance(field_value, list):
#             new_list = []
#             for item in field_value:
#                 if is_dataclass(item):
#                     new_item = find_and_replace(item, rewrite_func)
#                     if new_item is not None:
#                         new_list.append(new_item)
#                 else:
#                     new_list.append(item)
#             setattr(traversal_target, f.name, new_list)
#         elif is_dataclass(field_value):
#             new_value = find_and_replace(field_value, rewrite_func)
#             setattr(traversal_target, f.name, new_value)

#     replacement_target = rewrite_func(traversal_target)
#     if replacement_target is not None:
#         return replacement_target
#     else:
#         return traversal_target


# TODO:
# 1. Finish grammar and parser
# 2. Implement a TRS, based on TRAAT textbook (pg 80)
#
#
# 3. Compare language:
# - want better ease-of-use than python or haskell (maybe rust?)
# - want better performance than hand-optimized C, rust
# - see if our compiler does better than AI generated code
# - Should implement examples in python and haskell, see if they are good enough for testing, maybe find some benchmarks
