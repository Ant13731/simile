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
-