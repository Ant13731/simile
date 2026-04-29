from src.mod.data.types import (
    BaseType,
    BoolType,
    IntType,
    FloatType,
    StringType,
    SetType,
    BagType,
    RelationType,
    GenericType,
    TupleType,
)
from src.mod.data.types.traits import MinTrait, TraitCollection
import src.mod.data.ast_ as ast_


# TODO: What about composite types?
def get_primitive_types() -> dict[str, BaseType]:
    return {
        "int": IntType(),
        "str": StringType(),
        "float": FloatType(),
        "bool": BoolType(),
        "ℤ": SetType(IntType()),
        "ℕ": SetType(
            IntType(
                trait_collection=TraitCollection(
                    min_trait=MinTrait(ast_.Int("0")),
                )
            )
        ),
        "ℕ₁": SetType(
            IntType(
                trait_collection=TraitCollection(
                    min_trait=MinTrait(ast_.Int("1")),
                )
            )
        ),
    }
