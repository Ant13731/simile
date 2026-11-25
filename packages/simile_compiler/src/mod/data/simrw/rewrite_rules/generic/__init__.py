from src.mod.data.simrw.rewrite_rules.helpers import get_rewrite_rule_file_paths

NUMERIC_RULE_PATHS = get_rewrite_rule_file_paths("generic", ["sum"])
DESUGARING_RULE_PATHS = get_rewrite_rule_file_paths("generic", ["bag_sugar", "seq_sugar", "rel_sugar"])
COMPREHENSION_CONSTRUCTION_RULE_PATHS = get_rewrite_rule_file_paths("generic", ["comprehension_construction"])
BOOL_RULE_PATHS = get_rewrite_rule_file_paths("generic", ["bool", "dnf"])


GENERIC_REWRITE_RULE_PATHS = NUMERIC_RULE_PATHS + DESUGARING_RULE_PATHS + COMPREHENSION_CONSTRUCTION_RULE_PATHS + BOOL_RULE_PATHS
