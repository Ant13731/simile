"""
Ideas:
- Input file(s): ../mod/data/ast_/
- Output: ../../../../formalization/Simile/Data/AST.lean

- Import all ASTNodes in here
- Filter out the following: float, string, record, corresponding operators, imports
- Recursively do: if a node is a subclass of ASTNode, just mark it as ASTNode. list[x] -> List x

- We want to make the following struct in lean:
inductive ASTNode where
  | className (field1: Type1) (field2: Type2) ... (fieldN: TypeN)
  | ...
  | className (field1: Type1) (field2: Type2) ... (fieldN: TypeN)
- Also use the operator files for this

Should we use common_extended for this instead of introducing the *operator classes? would this be easier to prove? can try both
"""

from pathlib import Path
from src.mod.data import ast_

INPUT_DIR = Path(__file__).parent / "mod" / "data" / "ast_"
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "formalization" / "Simile" / "Data"

OUTPUT_AST_PATH = OUTPUT_DIR / "AST.lean"


def AST_to_lean():
    pre_symbol_table_asts = [
        ast_.Identifier,
        ast_.TupleIdentifier,
        ast_.TupleIdentifier,
        ast_.RecordDefIdentifier,
        ast_.ProcedureDefIdentifier,
    ]
    post_symbol_table_asts = [
        ast_.Symbol,
        ast_.TupleSymbol,
        ast_.MapletSymbol,
        ast_.RecordDefSymbol,
        ast_.ProcedureDefSymbol,
    ]
    post_optimizer_asts = [
        ast_.GeneratorSelection,
        ast_.CombinedGeneratorSelection,
        ast_.SingleGeneratorSelection,
        ast_.Loop,
    ]
    common_asts = [
        ast_.Int,
        # Float,
        # String,
        ast_.True_,
        ast_.False_,
        ast_.None_,
        #
        ast_.Quantifier3,
        ast_.Generator,
        ast_.QuantifierBody,
        ast_.IterGenerator,
        ast_.IterBodyEnd,
        ast_.Fold,
        ast_.IterBody,
        ast_.Iter,
        ast_.ControlFlowStmt,
        ast_.Enumeration,
        ast_.Type_,
        ast_.LambdaDef,
        # ast_.RecordAccess,
        ast_.Call,
        ast_.TypedName,
        ast_.Image,
        ast_.Assignment,
        ast_.TraitApplication,
        ast_.Return,
        ast_.Statements,
        ast_.Else,
        ast_.If,
        ast_.ElseIf,
        ast_.For,
        ast_.While,
        ast_.TupleLiteral,
        ast_.Import,
        ast_.Start,
        #
        ast_.Implies,
        # Equivalent,
        # NotEquivalent,
        #
        ast_.Add,
        ast_.Subtract,
        ast_.Multiply,
        ast_.Divide,
        ast_.IntDivide,
        ast_.Modulo,
        ast_.Exponent,
        ast_.LessThan,
        ast_.LessThanOrEqual,
        ast_.GreaterThan,
        ast_.GreaterThanOrEqual,
        ast_.Equal,
        ast_.NotEqual,
        ast_.Is,
        ast_.IsNot,
        ast_.In,
        ast_.NotIn,
        ast_.Union,
        ast_.Intersection,
        ast_.Difference,
        ast_.Subset,
        ast_.SubsetEq,
        ast_.Superset,
        ast_.SupersetEq,
        ast_.NotSubset,
        ast_.NotSubsetEq,
        ast_.NotSuperset,
        ast_.NotSupersetEq,
        ast_.Maplet,
        ast_.RelationOverriding,
        ast_.Composition,
        ast_.CartesianProduct,
        ast_.Upto,
        ast_.Concat,
        ast_.DomainSubtraction,
        ast_.DomainRestriction,
        ast_.RangeSubtraction,
        ast_.RangeRestriction,
        ast_.Relation,
        ast_.TotalRelation,
        ast_.SurjectiveRelation,
        ast_.TotalSurjectiveRelation,
        ast_.PartialFunction,
        ast_.TotalFunction,
        ast_.PartialInjection,
        ast_.TotalInjection,
        ast_.PartialSurjection,
        ast_.TotalSurjection,
        ast_.Bijection,
        ast_.Not,
        ast_.Negative,
        ast_.Inverse,
        ast_.And,
        ast_.Or,
        ast_.Forall,
        ast_.Exists,
        ast_.UnionAll,
        ast_.IntersectionAll,
        ast_.Sum,
        ast_.Product,
        ast_.Min,
        ast_.Max,
        ast_.Break,
        ast_.Continue,
        ast_.Skip,
        ast_.SequenceEnumeration,
        ast_.SetEnumeration,
        ast_.RelationEnumeration,
        ast_.BagEnumeration,
        ast_.SequenceComprehension,
        ast_.SetComprehension,
        ast_.RelationComprehension,
        ast_.BagComprehension,
    ]
