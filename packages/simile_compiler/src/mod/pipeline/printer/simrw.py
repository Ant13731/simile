from src.mod.data.simrw import GuardCondition, SimrwRule, SimrwAST
from src.mod.pipeline.printer.type_ import type_to_source
from src.mod.pipeline.printer.ast_ import ast_to_source, T


def simrw_ast_to_source(rewrite_rule: SimrwAST) -> str:
    ret = f"rule {rewrite_rule.name}:\n"
    ret += T + "vars:\n"
    if rewrite_rule.vars_:
        ret += "\n".join(var for var in add_prefix_whitespace(rewrite_rule.vars_).splitlines())
        ret += "\n"
    ret += T + "rewrite:\n"
    ret += f"{add_prefix_whitespace(rewrite_rule.rewrite_left)}\n"
    ret += T * 2 + "~>\n"
    ret += f"{add_prefix_whitespace(rewrite_rule.rewrite_right)}\n"
    if rewrite_rule.when:
        ret += T + "when:\n"
        ret += "\n".join(add_prefix_whitespace(condition) for condition in rewrite_rule.when)
        ret += "\n"
    return ret


def add_prefix_whitespace(text: str) -> str:
    return "\n".join(T * 2 + line for line in text.splitlines())


def simrw_to_source(rewrite_rule: SimrwRule) -> str:
    ret = f"rule {rewrite_rule.name()}:\n"
    ret += T + "vars:\n"
    if rewrite_rule.vars_:
        # TODO replacing _ with 000 to get around the assumption that types in simrw rules always have the form T[0-9]+ is a bit of a hack
        ret += f"\n".join(add_prefix_whitespace(f"{var}: {type_to_source(type_).replace("_","000")}") for var, type_ in rewrite_rule.vars_.items())
        ret += "\n"
    ret += T + f"rewrite:\n"
    ret += f"{add_prefix_whitespace(ast_to_source(rewrite_rule.rewrite_left))}\n"
    ret += T * 2 + "~>\n"
    ret += f"{add_prefix_whitespace(ast_to_source(rewrite_rule.rewrite_right))}\n"
    if rewrite_rule.when:
        ret += T + "when:\n"
        ret += f"\n".join(add_prefix_whitespace(guard_condition_to_source(condition)) for condition in rewrite_rule.when)
        ret += "\n"
    return ret


def guard_condition_to_source(guard_condition: GuardCondition) -> str:
    raise NotImplementedError("Guard condition to source code converter not implemented")  # TODO need to implement visitor pattern over all variable types of guards...
    return f"{guard_condition.name}()"
