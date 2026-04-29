# Redesigning ASTs

## Basic AST requirements
Metadata:
- file location
- start location
- end location

- operations have an `op_type` - should separate this into another base class? OperatorAST?
- quantifiers may be able to bind variables embedded within expressions, or they can have a full version with explicitly bound variables. We should have another pass to convert all non-fully-qualified quantifiers into fully qualified quantifiers (like desugaring). this can happen at ambiguous quantifiers stage

## Typed Addons
- type (inserted after type inference)

## To remove
- bound, free, well-formed?
- structurally equal?

## Functions
- convert_to_source
- convert_to_debug_string
    - include location, all fields
- is_leaf? (unused)
- find_and_replace
    - used in optimizer
- find_and_replace_with_func
- children
    - used in type analysis, ambiguous quantifiers, symbol table


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
