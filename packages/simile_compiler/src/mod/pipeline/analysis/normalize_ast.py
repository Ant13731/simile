from src.mod.data import ast_
from src.mod.data.types.error import SimileTypeError


def normalize_ast(node: ast_.ASTNode) -> ast_.ASTNode:
    """Promotes ASTs defined generically to their respective specific class based on the operator.
    For example, a Quantifier with a set operator will be promoted to a SetComprehension AST"""
    return node.find_and_replace_with_func(ast_promoter)


def ast_promoter(node: ast_.ASTNode) -> ast_.ASTNode | None:
    if isinstance(node, ast_.BinaryOp):
        return _promote_binary_op(node)
    if isinstance(node, ast_.RelationOp):
        return _promote_relation_op(node)
    if isinstance(node, ast_.ListOp):
        return _promote_list_op(node)
    if isinstance(node, ast_.UnaryOp):
        return _promote_unary_op(node)
    if isinstance(node, ast_.ControlFlowStmt):
        return _promote_control_flow_stmt(node)
    if isinstance(node, ast_.Quantifier):
        return _promote_quantifier(node)
    if isinstance(node, ast_.QualifiedQuantifier):
        return _promote_qualified_quantifier(node)
    if isinstance(node, ast_.Enumeration):
        return _promote_enumeration(node)
    return None


def _promote_binary_op(node: ast_.BinaryOp) -> ast_.ASTNode:
    match node.op_type:
        case ast_.BinaryOperator.IMPLIES:
            return ast_.Implies(node.left, node.right)
        case ast_.BinaryOperator.EQUIVALENT:
            return ast_.Equivalent(node.left, node.right)
        case ast_.BinaryOperator.NOT_EQUIVALENT:
            return ast_.NotEquivalent(node.left, node.right)
        case ast_.BinaryOperator.ADD:
            return ast_.Add(node.left, node.right)
        case ast_.BinaryOperator.SUBTRACT:
            return ast_.Subtract(node.left, node.right)
        case ast_.BinaryOperator.MULTIPLY:
            return ast_.Multiply(node.left, node.right)
        case ast_.BinaryOperator.DIVIDE:
            return ast_.Divide(node.left, node.right)
        case ast_.BinaryOperator.MODULO:
            return ast_.Modulo(node.left, node.right)
        case ast_.BinaryOperator.EXPONENT:
            return ast_.Exponent(node.left, node.right)
        case ast_.BinaryOperator.LESS_THAN:
            return ast_.LessThan(node.left, node.right)
        case ast_.BinaryOperator.LESS_THAN_OR_EQUAL:
            return ast_.LessThanOrEqual(node.left, node.right)
        case ast_.BinaryOperator.GREATER_THAN:
            return ast_.GreaterThan(node.left, node.right)
        case ast_.BinaryOperator.GREATER_THAN_OR_EQUAL:
            return ast_.GreaterThanOrEqual(node.left, node.right)
        case ast_.BinaryOperator.EQUAL:
            return ast_.Equal(node.left, node.right)
        case ast_.BinaryOperator.NOT_EQUAL:
            return ast_.NotEqual(node.left, node.right)
        case ast_.BinaryOperator.IS:
            return ast_.Is(node.left, node.right)
        case ast_.BinaryOperator.IS_NOT:
            return ast_.IsNot(node.left, node.right)
        case ast_.BinaryOperator.IN:
            return ast_.In(node.left, node.right)
        case ast_.BinaryOperator.NOT_IN:
            return ast_.NotIn(node.left, node.right)
        case ast_.BinaryOperator.UNION:
            return ast_.Union(node.left, node.right)
        case ast_.BinaryOperator.INTERSECTION:
            return ast_.Intersection(node.left, node.right)
        case ast_.BinaryOperator.DIFFERENCE:
            return ast_.Difference(node.left, node.right)
        case ast_.BinaryOperator.SUBSET:
            return ast_.Subset(node.left, node.right)
        case ast_.BinaryOperator.SUBSET_EQ:
            return ast_.SubsetEq(node.left, node.right)
        case ast_.BinaryOperator.SUPERSET:
            return ast_.Superset(node.left, node.right)
        case ast_.BinaryOperator.SUPERSET_EQ:
            return ast_.SupersetEq(node.left, node.right)
        case ast_.BinaryOperator.NOT_SUBSET:
            return ast_.NotSubset(node.left, node.right)
        case ast_.BinaryOperator.NOT_SUBSET_EQ:
            return ast_.NotSubsetEq(node.left, node.right)
        case ast_.BinaryOperator.NOT_SUPERSET:
            return ast_.NotSuperset(node.left, node.right)
        case ast_.BinaryOperator.NOT_SUPERSET_EQ:
            return ast_.NotSupersetEq(node.left, node.right)
        case ast_.BinaryOperator.MAPLET:
            return ast_.Maplet(node.left, node.right)
        case ast_.BinaryOperator.RELATION_OVERRIDING:
            return ast_.RelationOverriding(node.left, node.right)
        case ast_.BinaryOperator.COMPOSITION:
            return ast_.Composition(node.left, node.right)
        case ast_.BinaryOperator.CARTESIAN_PRODUCT:
            return ast_.CartesianProduct(node.left, node.right)
        case ast_.BinaryOperator.UPTO:
            return ast_.Upto(node.left, node.right)
        case ast_.BinaryOperator.DOMAIN_SUBTRACTION:
            return ast_.DomainSubtraction(node.left, node.right)
        case ast_.BinaryOperator.DOMAIN_RESTRICTION:
            return ast_.DomainRestriction(node.left, node.right)
        case ast_.BinaryOperator.RANGE_SUBTRACTION:
            return ast_.RangeSubtraction(node.left, node.right)
        case ast_.BinaryOperator.RANGE_RESTRICTION:
            return ast_.RangeRestriction(node.left, node.right)
        case ast_.BinaryOperator.CONCAT:
            return ast_.Concat(node.left, node.right)
        case ast_.BinaryOperator.INT_DIVIDE:
            return ast_.IntDivide(node.left, node.right)
    return node


def _promote_relation_op(node: ast_.RelationOp) -> ast_.ASTNode:
    match node.op_type:
        case ast_.RelationOperator.RELATION:
            return ast_.Relation(node.left, node.right)
        case ast_.RelationOperator.TOTAL_RELATION:
            return ast_.TotalRelation(node.left, node.right)
        case ast_.RelationOperator.SURJECTIVE_RELATION:
            return ast_.SurjectiveRelation(node.left, node.right)
        case ast_.RelationOperator.TOTAL_SURJECTIVE_RELATION:
            return ast_.TotalSurjectiveRelation(node.left, node.right)
        case ast_.RelationOperator.PARTIAL_FUNCTION:
            return ast_.PartialFunction(node.left, node.right)
        case ast_.RelationOperator.TOTAL_FUNCTION:
            return ast_.TotalFunction(node.left, node.right)
        case ast_.RelationOperator.PARTIAL_INJECTION:
            return ast_.PartialInjection(node.left, node.right)
        case ast_.RelationOperator.TOTAL_INJECTION:
            return ast_.TotalInjection(node.left, node.right)
        case ast_.RelationOperator.PARTIAL_SURJECTION:
            return ast_.PartialSurjection(node.left, node.right)
        case ast_.RelationOperator.TOTAL_SURJECTION:
            return ast_.TotalSurjection(node.left, node.right)
        case ast_.RelationOperator.BIJECTION:
            return ast_.Bijection(node.left, node.right)
    return node


def _promote_list_op(node: ast_.ListOp) -> ast_.ASTNode:
    match node.op_type:
        case ast_.ListOperator.AND:
            return ast_.And(node.items)
        case ast_.ListOperator.OR:
            return ast_.Or(node.items)
    return node


def _promote_unary_op(node: ast_.UnaryOp) -> ast_.ASTNode:
    match node.op_type:
        case ast_.UnaryOperator.NOT:
            return ast_.Not(node.value)
        case ast_.UnaryOperator.NEGATIVE:
            return ast_.Negative(node.value)
        case ast_.UnaryOperator.POWERSET:
            return ast_.Powerset(node.value)
        case ast_.UnaryOperator.NONEMPTY_POWERSET:
            return ast_.NonemptyPowerset(node.value)
        case ast_.UnaryOperator.INVERSE:
            return ast_.Inverse(node.value)
    return node


def _promote_control_flow_stmt(node: ast_.ControlFlowStmt) -> ast_.ASTNode:
    match node.op_type:
        case ast_.ControlFlowOperator.BREAK:
            return ast_.Break()
        case ast_.ControlFlowOperator.CONTINUE:
            return ast_.Continue()
        case ast_.ControlFlowOperator.SKIP:
            return ast_.Skip()
    return node


def _promote_quantifier(node: ast_.Quantifier) -> ast_.ASTNode:
    match node.op_type:
        case ast_.QuantifierOperator.UNION_ALL:
            return ast_.UnionAll(node.predicate, node.expression)
        case ast_.QuantifierOperator.INTERSECTION_ALL:
            return ast_.IntersectionAll(node.predicate, node.expression)
        case ast_.QuantifierOperator.SUM:
            return ast_.Sum(node.predicate, node.expression)
        case ast_.QuantifierOperator.PRODUCT:
            return ast_.Product(node.predicate, node.expression)
        case ast_.QuantifierOperator.SEQUENCE:
            return ast_.SequenceComprehension(node.predicate, node.expression)
        case ast_.QuantifierOperator.SET:
            return ast_.SetComprehension(node.predicate, node.expression)
        case ast_.QuantifierOperator.RELATION:
            return ast_.RelationComprehension(node.predicate, node.expression)
        case ast_.QuantifierOperator.BAG:
            return ast_.BagComprehension(node.predicate, node.expression)
        case ast_.QuantifierOperator.FORALL:
            return ast_.Forall(node.predicate, node.expression)
        case ast_.QuantifierOperator.EXISTS:
            return ast_.Exists(node.predicate, node.expression)
    return node


def _promote_qualified_quantifier(node: ast_.QualifiedQuantifier) -> ast_.ASTNode:
    match node.op_type:
        case ast_.QuantifierOperator.UNION_ALL:
            return ast_.QualifiedUnionAll(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.INTERSECTION_ALL:
            return ast_.QualifiedIntersectionAll(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.SUM:
            return ast_.QualifiedSum(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.PRODUCT:
            return ast_.QualifiedProduct(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.SEQUENCE:
            return ast_.QualifiedSequenceComprehension(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.SET:
            return ast_.QualifiedSetComprehension(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.RELATION:
            return ast_.QualifiedRelationComprehension(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.BAG:
            return ast_.QualifiedBagComprehension(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.FORALL:
            return ast_.QualifiedForall(node.bound_identifiers, node.predicate, node.expression)
        case ast_.QuantifierOperator.EXISTS:
            return ast_.QualifiedExists(node.bound_identifiers, node.predicate, node.expression)
    return node


def _promote_enumeration(node: ast_.Enumeration) -> ast_.ASTNode:
    match node.op_type:
        case ast_.CollectionOperator.SEQUENCE:
            return ast_.SequenceEnumeration(node.items)
        case ast_.CollectionOperator.SET:
            return ast_.SetEnumeration(node.items)
        case ast_.CollectionOperator.RELATION:
            return ast_.RelationEnumeration(node.items)
        case ast_.CollectionOperator.BAG:
            return ast_.BagEnumeration(node.items)
    return node
