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
