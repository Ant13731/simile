from pathlib import Path

from src.mod.data.ast_.operators import (
    BinaryOperator,
    RelationOperator,
    UnaryOperator,
    ListOperator,
    QuantifierOperator,
    ControlFlowOperator,
    CollectionOperator,
)


def main():
    path_str = r"packages\simile_compiler\src\mod\ast_\ast_nodes_generated.py"
    output_file_path = Path(path_str)

    print(f"Generating operators from types to {path_str}...")

    ret_str = f"""
# This file is auto-generated through {path_str}. Do not edit manually.
from dataclasses import dataclass, field

from src.mod.ast_.ast_node_operators import (
    BinaryOperator,
    RelationOperator,
    UnaryOperator,
    ListOperator,
    QuantifierOperator,
    ControlFlowOperator,
    CollectionOperator,
    Operators,
)
from src.mod.ast_.ast_nodes import (
    True_,
    BinaryOp,
    RelationOp,
    ListOp,
    UnaryOp,
    Quantifier,
    ControlFlowStmt,
    Enumeration,
)
"""

    corresponding_classes_and_op_types = [
        (BinaryOperator, "BinaryOp"),
        (RelationOperator, "RelationOp"),
        (ListOperator, "ListOp"),
        (UnaryOperator, "UnaryOp"),
        (ControlFlowOperator, "ControlFlowStmt"),
        (QuantifierOperator, "Quantifier"),
        (CollectionOperator, "Enumeration"),
    ]

    for op_type, class_name in corresponding_classes_and_op_types:
        for op in op_type:
            name = op.name.replace("_", " ").title().replace(" ", "")
            if op_type == CollectionOperator:
                name += "Enumeration"
            elif op_type == QuantifierOperator:
                if op.is_collection_operator():
                    name += "Comprehension"
                elif op.is_bool_quantifier():
                    continue

            print(f"Generating {name} ({class_name})...")
            ret_str += f"""
@dataclass
class {name}({class_name}):
    op_type: {op_type.__name__} = {op_type.__name__}.{op.name}

"""
    for op in QuantifierOperator:
        if not op.is_bool_quantifier():
            continue
        print(f"Generating {name} (Quantifier)...")
        ret_str += f"""
@dataclass
class {op.name.title()}(Quantifier):
    expression: True_ = field(default_factory=True_)
    op_type: QuantifierOperator = QuantifierOperator.{op.name}

"""
    # def __eq__(self, other: object) -> bool:
    #         if not isinstance(other, {class_name}):
    #             return False
    #         return super().__eq__(other)
    # def __eq__(self, other: object) -> bool:
    #         if not isinstance(other, Quantifier):
    #             return False
    #         return super().__eq__(other)

    with open(output_file_path, "w") as f:
        f.write(ret_str)


if __name__ == "__main__":
    main()
