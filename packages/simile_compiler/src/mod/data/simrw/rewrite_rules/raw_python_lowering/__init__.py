from src.mod.data.simrw.rewrite_rules.helpers import get_rewrite_rule_file_paths
from src.mod.data.simrw.rewrite_rules.raw_python_lowering.quantifier import RAW_PYTHON_QUANTIFICATION_RULES

_FILE_NAMES = [
    "relation_op",
    "statements",
]

RAW_PYTHON_REWRITE_RULE_PATHS = get_rewrite_rule_file_paths("raw_python_lowering", _FILE_NAMES)
# Hardcoded inside of simrw files when we need to refer to the simile-python library
RAW_PYTHON_SIMILE_LIBRARY_NAME = "simile_python_raw"
