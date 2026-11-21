from dataclasses import dataclass


@dataclass
class SimrwAST:
    name: str
    vars_: str
    rewrite_left: str
    rewrite_right: str
    when: list[str]
