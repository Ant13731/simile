from src.mod.pipeline.optimizer.v2 import GuardCondition, RewriteRule, SimrwAST
from src.mod.pipeline.printers.type_ import type_to_source
from src.mod.pipeline.printers.ast_ import ast_to_source


def simrw_ast_to_source(rewrite_rule: SimrwAST) -> str:
    ret = f"rule {rewrite_rule.name}:\n"
    ret += "\tvars:\n"
    if rewrite_rule.vars_:
        ret += "\n".join(var for var in add_prefix_whitespace(rewrite_rule.vars_).splitlines())
        ret += "\n"
    ret += f"\trewrite:\n"
    ret += f"{add_prefix_whitespace(rewrite_rule.rewrite_left)}\n"
    ret += "\t\t~>\n"
    ret += f"{add_prefix_whitespace(rewrite_rule.rewrite_right)}\n"
    if rewrite_rule.when:
        ret += "\twhen:\n"
        ret += "\n".join(add_prefix_whitespace(condition) for condition in rewrite_rule.when)
        ret += "\n"
    return ret


def add_prefix_whitespace(text: str) -> str:
    return "\n".join("\t\t" + line for line in text.splitlines())


def simrw_to_source(rewrite_rule: RewriteRule) -> str:
    ret = f"rule {rewrite_rule.name}:\n"
    ret += "\tvars:\n"
    if rewrite_rule.vars_:
        ret += "\t\t"
        ret += "\n\t\t".join(f"{var}: {type_to_source(type_)}" for var, type_ in rewrite_rule.vars_.items())
        ret += "\n"
    ret += f"\trewrite:\n"
    ret += f"\t\t{ast_to_source(rewrite_rule.rewrite_left)}\n"
    ret += "\t\t~>\n"
    ret += f"\t\t{ast_to_source(rewrite_rule.rewrite_right)}\n"
    if rewrite_rule.when:
        ret += "\twhen:\n"
        ret += "\t\t"
        ret += "\n\t\t".join(guard_condition_to_source(condition) for condition in rewrite_rule.when)
        ret += "\n"
    return ret


def guard_condition_to_source(guard_condition: GuardCondition) -> str:
    raise NotImplementedError  # TODO need to implement visitor pattern over all variable types of guards...
    return f"{guard_condition.name}()"
