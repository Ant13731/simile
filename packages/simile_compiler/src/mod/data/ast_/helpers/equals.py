from typing import Any
from loguru import logger

from src.mod.data.ast_.base import ASTNode
from src.mod.data.ast_.parser_only import Identifier
from src.mod.data.ast_.common import (
    ListOp,
    Statements,
    For,
)
from src.mod.data.ast_.symbol_table_env import Environment


def structurally_equal(self: ASTNode, other: ASTNode) -> bool:
    """Check if two AST nodes are structurally equal (i.e., have the same AST structure aside from variable names)."""

    # there should be a one-to-one mapping of variable names from this node to the other node
    # FIXME USE ENVIRONMENT!!!!!!!!!!!!!Does this need scoping? like envs? probably
    rename_env = Environment[str]()

    def structurally_equal_aux(self_: ASTNode | Any, other_: ASTNode | Any, env: Environment[str]) -> bool:
        logger.trace(f"Comparing {self_} with {other_}")

        if isinstance(self_, Identifier) and isinstance(other_, Identifier):
            # If both are identifiers, check if they are the same or if they can be renamed
            if env.get(self_.name) is not None:
                if env.get(self_.name) == other_.name:
                    return True

                logger.debug(f"FAILED: {self_.name} and {other_.name} do not match")
                return False

            # Other name is somewhere in the var table but doesn't correspond to this var...
            if env.get_value(other_.name):
                logger.debug(f"FAILED: other variable name {other_.name} is in the environment but does have a corresponding match with {self_.name}")
                return False

            # Add to variable rename table
            logger.trace(f"Adding rename mapping: {self_.name} -> {other_.name}")
            env.put(self_.name, other_.name)
            return True

        # If not an ASTNode, nothing special to check, just compare values
        if not isinstance(self_, ASTNode):
            if self_ == other_:
                return True

            logger.debug(f"FAILED: {self_} and {other_} do not match")
            return False

        # If self is an ast node but other is not, they are not structurally equal
        if not isinstance(other_, ASTNode):
            logger.debug(f"FAILED: {self_} is an ASTNode but {other_} is not")
            return False

        # Eliminate superfluous And, Or, wrapped statements, etc.
        if isinstance(self_, (ListOp, Statements)) and len(self_.items) == 1:
            self_ = self_.items[0]
        if isinstance(other_, (ListOp, Statements)) and len(other_.items) == 1:
            other_ = other_.items[0]

        if isinstance(self_, Statements) and isinstance(other_, Statements):
            logger.trace("New comparison environment - statements")
            env = Environment(previous=env)
        if isinstance(self_, For) and isinstance(other_, For):  # for loop binds a variable that should not be accessed outside of the loop
            logger.trace("New comparison environment - for loop")
            env = Environment(previous=env)

        # Call on all other fields
        for self_f, other_f in zip(self_.children(), other_.children()):
            if not structurally_equal_aux(self_f, other_f, env):
                logger.debug(f"FAILED (propagated): {self_f} and {other_f} do not match")
                return False
        return True

    return structurally_equal_aux(self, other, rename_env)
