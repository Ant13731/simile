from src.mod.data import ast_
from src.mod.pipeline.analysis import SemanticAnalysis
from src.mod.pipeline.codegen.raw_python import Printer


def lower_to_raw_python(semantic_analysis: SemanticAnalysis) -> str:
    return Printer().print(semantic_analysis.ast)


def lower_to_python(semantic_analysis: SemanticAnalysis) -> str:
    raise NotImplementedError


def lower_to_rust(semantic_analysis: SemanticAnalysis) -> str:
    raise NotImplementedError
