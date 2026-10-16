inductive IdentifierAST where
  |


inductive AST where
  | int: String -> AST
  -- | float: String -> AST
  -- | string: String -> AST
  | true
  | false
  | none
  | identifier: IdentifierAST -> AST
  | binaryOp: AST -> AST -> BinaryOperator -> AST
  | relationOp: AST -> AST -> RelationOperator -> AST
  | unaryOp: AST -> UnaryOperator -> AST
  | listOp: List AST -> ListOperator -> AST
  | quantifier: AST -> QuantifierOperator -> AST
  | generator: List AST






inductive Expr where

  -- Literals
  | boolLiteral: Bool -> Expr
  | intLiteral: Int -> Expr
  | setEnumeration: Set Expr -> Expr
  | relationEnumeration: Relation Expr -> Expr
  | bagEnumeration: Multiset Expr -> Expr
  | sequenceEnumeration: List Expr -> Expr
  | tupleEnumeration: List Expr -> Expr
  | type: Expr -> Expr
  -- Definitions
  | procedureDef: List Expr -> Expr -> Expr
  -- | recordDef
  -- | import
  -- Base expr operations/types
  | cast: Expr -> Expr
  | castWithTrait: Expr -> Expr -> Expr
  | equals: Expr -> Expr -> Expr
  | notEquals: Expr -> Expr -> Expr
  -- Bool
  | not: Expr -> Expr
  | equivalent: Expr -> Expr -> Expr
  | notEquivalent: Expr -> Expr -> Expr
  | implies: Expr -> Expr -> Expr
  | and: List Expr -> Expr
  | or: List Expr -> Expr
  -- Int
  --- Comparison
  | greaterThan: Expr -> Expr -> Expr
  | greaterThanEquals: Expr -> Expr -> Expr
  | lessThan: Expr -> Expr -> Expr
  | lessThanEquals: Expr -> Expr -> Expr
  --- Arithmetic
  | negate: Expr -> Expr
  | intDivide: Expr -> Expr -> Expr
  | modulo: Expr -> Expr -> Expr
  | add: Expr -> Expr -> Expr
  | subtract: Expr -> Expr -> Expr
  | divide: Expr -> Expr -> Expr
  | multiply: Expr -> Expr -> Expr
  | power: Expr -> Expr -> Expr
  --- Set
  | upto: Expr -> Expr -> Expr
  -- Set
  | cardinality: Expr -> Expr
  | in: Expr -> Expr -> Expr
  | notIn: Expr -> Expr -> Expr
  | union: Expr -> Expr -> Expr
  | intersection: Expr -> Expr -> Expr
  | difference: Expr -> Expr -> Expr
  | cartesianProduct: Expr -> Expr -> Expr
  | isSubset: Expr -> Expr -> Expr
  | isSubsetEquals: Expr -> Expr -> Expr
  | isSuperset: Expr -> Expr -> Expr
  | isSupersetEquals: Expr -> Expr -> Expr
  | notIsSubset: Expr -> Expr -> Expr
  | notIsSubsetEquals: Expr -> Expr -> Expr
  | notIsSuperset: Expr -> Expr -> Expr
  | notIsSupersetEquals: Expr -> Expr -> Expr
  -- Relation
  | inverse: Expr -> Expr
  | domain: Expr -> Expr
  | range: Expr -> Expr
  | composition: Expr -> Expr -> Expr
  | functionCall: Expr -> Expr -> Expr
  | image: Expr -> Expr -> Expr
  | overriding: Expr -> Expr -> Expr
  | domainRestriction: Expr -> Expr -> Expr
  | domainSubtraction: Expr -> Expr -> Expr
  | rangeRestriction: Expr -> Expr -> Expr
  | rangeSubtraction: Expr -> Expr -> Expr
  | bagImage: Expr -> Expr -> Expr
  -- Bag
  | size: Expr -> Expr
  | bagUnion: Expr -> Expr -> Expr
  | bagIntersection: Expr -> Expr -> Expr
  | bagAdd: Expr -> Expr -> Expr
  | bagDifference: Expr -> Expr -> Expr
  -- Sequence
  | concat: Expr -> Expr -> Expr
  -- Tuple
  | tupleIndex: Expr -> Expr -> Expr
  -- Quantifier
  | quantifier: Expr
  | forall
  | exists
  | unionAll
  | intersectionAll
  | setComprehension
  | relationComprehension
  | bagComprehension
  | sequenceComprehension
  | sum
  | product
  | min
  | max
  | iter
  | fold
  -- Composite
  | procedureCall
    -- Also stores things like powerset, map, choice, sum, product, min, max, mapMin, mapMax
  -- | recordAccess
