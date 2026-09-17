from src.mod.data.traits.base import (
    SimileLiteralAsPythonOrderable,
    SimileLiteralAsPython,
    BaseTrait,
    ImmutableTrait,
    LiteralTrait,
    UndefinedTrait,
)
from src.mod.data.traits.orderable import (
    OrderableTrait,
    MinTrait,
    MaxTrait,
)
from src.mod.data.traits.set_ import (
    DomainTrait,
    IterableTrait,
    UniqueTrait,
    EmptyTrait,
    SizeTrait,
    TotalTrait,
)
from src.mod.data.traits.relation import (
    OneToManyTrait,
    ManyToOneTrait,
    TotalOnDomainTrait,
    TotalOnRangeTrait,
    RelationalDomainTrait,
    RelationalRangeTrait,
)
from src.mod.data.traits.meta import (
    GenericBoundTrait,
)
from src.mod.data.traits.procedure import (
    TreatAsExprTrait,
)
from src.mod.data.traits.trait_operations import (
    MergeTraitBehaviour,
    Traits,
)
from src.mod.data.traits.error import SimileTraitError
