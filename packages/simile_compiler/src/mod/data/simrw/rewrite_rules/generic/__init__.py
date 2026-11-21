from src.mod.data.simrw.rewrite_rules.helpers import get_rewrite_rule_file_paths

_FILE_NAMES = [
    "bag_sugar",
    "bool",
    "comprehension_construction",
    "dnf",
    "rel_sugar",
    "seq_sugar",
    "sum",
]

GENERIC_REWRITE_RULE_PATHS = get_rewrite_rule_file_paths("generic", _FILE_NAMES)
