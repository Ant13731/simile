from loguru import logger

from src.mod.pipeline.optimizer.v2.rewrite_phase import RewritePhase
from src.mod.data.simrw.rewrite_rules.raw_python_lowering import (
    RAW_PYTHON_REWRITE_RULE_PATHS,
    RAW_PYTHON_QUANTIFICATION_RULES,
)
from src.mod.data.simrw.rewrite_rules.generic import (
    NUMERIC_RULE_PATHS,
    DESUGARING_RULE_PATHS,
    COMPREHENSION_CONSTRUCTION_RULE_PATHS,
    BOOL_RULE_PATHS,
)

RAW_PYTHON_LOWERING_PHASE = RewritePhase(
    "raw_python_lowering",
    [
        *RAW_PYTHON_REWRITE_RULE_PATHS,
        *RAW_PYTHON_QUANTIFICATION_RULES,
    ],
)

GENERIC_NUMERIC_PHASE = RewritePhase(
    "numeric",
    NUMERIC_RULE_PATHS,
)
GENERIC_DESUGARING_PHASE = RewritePhase(
    "desugaring",
    DESUGARING_RULE_PATHS,
)
GENERIC_COMPREHENSION_CONSTRUCTION_PHASE = RewritePhase(
    "comprehension_construction",
    COMPREHENSION_CONSTRUCTION_RULE_PATHS,
)
GENERIC_BOOL_NORMALIZATION_PHASE = RewritePhase(
    "bool_normalization",
    BOOL_RULE_PATHS,
)
