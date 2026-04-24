# ASTNodes - Type Analysis

Major questions:

- how to populate every AST node with its (resulting) type
- literals + expressions can be built straightforward
- Statements themselves have no type, but may have an effect on the environment
  - Eg. Assignment, import
- How to deal with identifiers, function calls, indirection

ASTNode list

## Constructs that lookup effects

- [>] Identifier
- [>] IdentList
- [>] TypedName

- [>] LambdaDef

- [>] StructAccess
- [>] FunctionCall
- [>] Indexing

## Constructs that add to effects

- [>] Statements
-
- [ ] Assignment

- [>] StructDef
- [>] EnumDef
- [>] FunctionDef

- [>] ImportAll
- [>] Import

## Expressions

- [>] Type\_
- [>] Int
- [>] Float
- [>] String
- [>] True
- [>] False
- [>] None
- [>] BinaryOp
- [>] RelationOp
- [>] UnaryOp
- [>] ListOp
- [>] BoolQuantifier
- [>] Quantifier
- [>] Enumeration
- [>] Comprehension
- [>] Return

## Non-effectful statements (in the context of direct types)

- [>] ControlFlowStmt
- [>] Start
- [>] If
- [>] Elif
- [>] Else
- [>] For
- [>] While

# How should we organize the AST

- Literals
  - Int
  - Float
  - String
  - True
  - False
  - None
  - Enumeration
- Identifiers
  - Identifier
  - StructAccess
  - IdentList
  - TypedName
- Expressions
  - UnaryOp
  - BinaryOp
  - RelationOp
  - ListOp
- Quantifiers
  - BoolQuantifier
  - Quantifier
  - Comprehension
  - LambdaDef
- Type
- Calls
  - Call
  - Image
- Assignment
- ControlFlow
  - Return
  - ControlFlowStmt
  - If
  - Else
  - Elif
  - For
  - While
- Statements
- Definitions
  - StructDef
  - ProcedureDef
- Import
  - ImportAll
- Start
