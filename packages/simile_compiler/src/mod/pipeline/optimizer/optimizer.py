from typing import ClassVar

from loguru import logger

from src.mod.data import ast_
from src.mod.pipeline.optimizer.rewrite_collection import RewriteCollection


def collection_optimizer(ast: ast_.ASTNode, matching_phases: list[type[RewriteCollection]]) -> ast_.ASTNode:
    for matching_phase in matching_phases:
        logger.debug(f"Applying matching phase: {matching_phase.__name__}")
        ast = matching_phase().normalize(ast)
    return ast
