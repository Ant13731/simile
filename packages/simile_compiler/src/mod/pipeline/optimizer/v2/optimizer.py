from src.mod.data import ast_
from src.mod.pipeline.analysis import SemanticAnalysis
from src.mod.pipeline.optimizer.v2.rewrite_phases import RAW_PYTHON_LOWERING_PHASE


def optimize(semantic_analysis: SemanticAnalysis):
    # TODO:
    # 1. generic phases
    # 2. ADT -> CDT
    # 3. specialized phases
    # 4. ? AST to then pass to other lower-er functions?
    raise NotImplementedError


def lower_for_raw_python(semantic_analysis: SemanticAnalysis) -> SemanticAnalysis:
    # TODO FIXME how can we guarantee phase application leaves semantic analysis in a consistent state
    semantic_analysis.ast = RAW_PYTHON_LOWERING_PHASE.apply_phase(
        semantic_analysis.ast,
        semantic_analysis.type_synthesizer,
    )
    return semantic_analysis
