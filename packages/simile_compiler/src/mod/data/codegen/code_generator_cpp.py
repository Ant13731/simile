from functools import singledispatchmethod
from dataclasses import dataclass, field
from typing import ClassVar, Any

from src.mod.data import ast_
from src.mod.data.codegen.code_generator_base import CodeGenerator, CodeGeneratorError


@dataclass
class CPPCodeGenerator(CodeGenerator):
    ast: ast_.ASTNode
    new_symbol_table: ast_.Environment = field(init=False)

    def __post_init__(self) -> None:
        self.new_symbol_table = ast_.Environment(
            table={name: CPPCodeGenerator.type_translator(typ, name) for name, typ in ast_.STARTING_ENVIRONMENT.table.items()},
        )

    @classmethod
    def type_translator(cls, simile_type: ast_.SimileType, def_name: str = "") -> str:
        """Translate Simile types to C++ types.

        Args:
            simile_type (ast_.SimileType): The Simile type to translate.
            def_name (str, optional): The name of the definition, if applicable (only used for function, enum, and struct definitions). Defaults to "".
        """
        match simile_type:
            case ast_.BaseSimileType.PosInt | ast_.BaseSimileType.Nat:
                return "unsigned long long"
            case ast_.BaseSimileType.Int:
                return "long long"
            case ast_.BaseSimileType.Float:
                return "double"
            case ast_.BaseSimileType.String:
                return "std::string"
            case ast_.BaseSimileType.Bool:
                return "bool"
            case ast_.BaseSimileType.None_:
                return "null"
            case ast_.PairType(left, right):
                return f"std::pair<{cls.type_translator(left)}, {cls.type_translator(right)}>"
            case ast_.SetType(ast_.PairType(left, right), _):
                return f"std::unordered_map<{cls.type_translator(left)}, {cls.type_translator(right)}>"
            case ast_.SetType(element_type, _):
                return f"std::unordered_set<{cls.type_translator(element_type)}>"
            case ast_.StructTypeDef(fields):
                return f"struct {def_name} {{ {''.join(f'{cls.type_translator(field[1])} {field[0]};' for field in fields.items())} }};"
            case ast_.EnumTypeDef(members):
                return f"enum {def_name} {{ {', '.join(members)} }};"
            case ast_.ProcedureTypeDef(arg_types, return_type):
                return f"{cls.type_translator(return_type)} {def_name}({', '.join(cls.type_translator(arg) for arg in arg_types.values())})"
            case ast_.ModuleImports(import_objects):
                raise ValueError(f"Module imports are not supported in C++ code generation yet. Got: {simile_type}")
            case ast_.TypeUnion(types):
                raise ValueError(f"Union types are not supported in C++ code generation. Got: {simile_type}")
            case ast_.DeferToSymbolTable(lookup_type):
                raise ValueError(f"DeferToSymbolTable types are not supported in C++ code generation (they should be resolved). Got: {simile_type}")
        raise ValueError(f"Unsupported Simile type for C++ translation: {simile_type}")

    def preamble(self) -> str:
        """Generate the C++ preamble."""
        return """
#include <iostream>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <string>
#include <cmath>
#include <algorithm>

// code from https://stackoverflow.com/questions/48299390/check-if-unordered-set-contains-all-elements-in-other-unordered-set-c
template <typename T>
bool is_subset_of(const std::unordered_set<T>& a, const std::unordered_set<T>& b)
{
    // return true if all members of a are also in b
    if (a.size() > b.size())
        return false;

    if (a == b) return true;

    auto const not_found = b.end();
    for (auto const& element: a)
        if (b.find(element) == not_found)
            return false;

    return true;
}

"""

    def generate(self) -> str:
        if self.ast._env is None:
            raise ValueError("AST environment should have been populated before code generation (see analysis module).")

        ret = ""
        ret += self.preamble()
        ret += self._generate_code(self.ast)

        return ret

    @singledispatchmethod
    def _generate_code(self, ast: ast_.ASTNode) -> str:
        """Auxiliary function for generating LLVM code based on the type of AST node. See :func:`generate_llvm_code`."""
        raise NotImplementedError(f"Code generation not implemented for node type: {type(ast)} with value {ast}")

    @_generate_code.register
    def _(self, ast: ast_.Identifier) -> str:
        # should we lookup the type here?
        return ast.name

    @_generate_code.register
    def _(self, ast: ast_.Literal) -> str:
        match ast:
            case ast_.Int(value) | ast_.Float(value):
                return value
            case ast_.String(value):
                return f'"{value}"'
            case ast_.True_():
                return "true"
            case ast_.False_():
                return "false"
            case ast_.None_():
                return "null"

        raise CodeGeneratorError(f"Unsupported literal type for C++ code generation: {type(ast)} with value {ast}")

    @_generate_code.register
    def _(self, ast: ast_.TupleIdentifier) -> str:
        return ", ".join(self._generate_code(ident) for ident in ast.items)

    @_generate_code.register
    def _(self, ast: ast_.BinaryOp) -> str:
        match ast.op_type:
            case ast_.BinaryOperator.IMPLIES:
                return f"({self._generate_code(ast.left)} ? {self._generate_code(ast.right)} : true)"
            # case ast_.BinaryOperator.REV_IMPLIES:
            #     return f"({self._generate_code(ast.right)} ? {self._generate_code(ast.left)} : true)"
            case ast_.BinaryOperator.EQUIVALENT | ast_.BinaryOperator.EQUAL:
                return f"({self._generate_code(ast.left)} == {self._generate_code(ast.right)})"
            case ast_.BinaryOperator.NOT_EQUIVALENT | ast_.BinaryOperator.NOT_EQUAL:
                return f"({self._generate_code(ast.left)} != {self._generate_code(ast.right)})"
            case (
                ast_.BinaryOperator.ADD
                | ast_.BinaryOperator.SUBTRACT
                | ast_.BinaryOperator.MULTIPLY
                | ast_.BinaryOperator.DIVIDE
                | ast_.BinaryOperator.MODULO
                | ast_.BinaryOperator.LESS_THAN
                | ast_.BinaryOperator.LESS_THAN_OR_EQUAL
                | ast_.BinaryOperator.GREATER_THAN
                | ast_.BinaryOperator.GREATER_THAN_OR_EQUAL
            ):
                return f"({self._generate_code(ast.left)} {ast.op_type.value} {self._generate_code(ast.right)})"
            case ast_.BinaryOperator.EXPONENT:
                return f"std::pow({self._generate_code(ast.left)}, {self._generate_code(ast.right)})"
            # case ast_.BinaryOperator.IS:
            # case ast_.BinaryOperator.IS_NOT:
            case ast_.BinaryOperator.IN:
                return f"({self._generate_code(ast.right)}.contains({self._generate_code(ast.left)}))"
            case ast_.BinaryOperator.NOT_IN:
                return f"!({self._generate_code(ast.right)}.contains({self._generate_code(ast.left)}))"
            # case ast_.BinaryOperator.UNION:
            # case ast_.BinaryOperator.INTERSECTION:
            # case ast_.BinaryOperator.DIFFERENCE:
            case ast_.BinaryOperator.SUBSET:
                return f"(a != b && is_subset_of({self._generate_code(ast.left)}, {self._generate_code(ast.right)}))"
            case ast_.BinaryOperator.SUBSET_EQ:
                return f"is_subset_of({self._generate_code(ast.left)}, {self._generate_code(ast.right)})"
            case ast_.BinaryOperator.SUPERSET:
                return f"(a != b && is_subset_of({self._generate_code(ast.right)}, {self._generate_code(ast.left)}))"
            case ast_.BinaryOperator.SUPERSET_EQ:
                return f"is_subset_of({self._generate_code(ast.right)}, {self._generate_code(ast.left)})"
            case ast_.BinaryOperator.NOT_SUBSET:
                return f"!(a != b && is_subset_of({self._generate_code(ast.left)}, {self._generate_code(ast.right)}))"
            case ast_.BinaryOperator.NOT_SUBSET_EQ:
                return f"!is_subset_of({self._generate_code(ast.left)}, {self._generate_code(ast.right)})"
            case ast_.BinaryOperator.NOT_SUPERSET:
                return f"!(a != b && is_subset_of({self._generate_code(ast.right)}, {self._generate_code(ast.left)}))"
            case ast_.BinaryOperator.NOT_SUPERSET_EQ:
                return f"!is_subset_of({self._generate_code(ast.right)}, {self._generate_code(ast.left)})"
            case ast_.BinaryOperator.MAPLET:
                return f"std::make_pair({self._generate_code(ast.left)}, {self._generate_code(ast.right)})"
            # case ast_.BinaryOperator.RELATION_OVERRIDING:
            # case ast_.BinaryOperator.COMPOSITION:
            # case ast_.BinaryOperator.CARTESIAN_PRODUCT:
            # case ast_.BinaryOperator.UPTO:
            #     return f"std::unordered_set{{ {self._generate_code(ast.left)}, {self._generate_code(ast.right)} }}"
            # case ast_.BinaryOperator.DOMAIN_SUBTRACTION:
            # case ast_.BinaryOperator.DOMAIN_RESTRICTION:
            # case ast_.BinaryOperator.RANGE_SUBTRACTION:
            # case ast_.BinaryOperator.RANGE_RESTRICTION:
        raise CodeGeneratorError(f"Binary operator {ast.op_type} is not supported in C++ code generation.")

    @_generate_code.register
    def _(self, ast: ast_.RelationOp) -> str:
        raise CodeGeneratorError(f"Relation operator {ast.op_type} is not supported in C++ code generation.")

    @_generate_code.register
    def _(self, ast: ast_.UnaryOp) -> str:
        match ast.op_type:
            case ast_.UnaryOperator.NOT:
                return f"!{self._generate_code(ast.value)}"
            case ast_.UnaryOperator.NEGATIVE:
                return f"-{self._generate_code(ast.value)}"
            # case ast_.UnaryOperator.POWERSET:
            # case ast_.UnaryOperator.NONEMPTY_POWERSET:
            # case ast_.UnaryOperator.INVERSE:
        raise CodeGeneratorError(f"Unary operator {ast.op_type} is not supported in C++ code generation.")

    @_generate_code.register
    def _(self, ast: ast_.ListOp) -> str:
        match ast.op_type:
            case ast_.ListOperator.AND:
                return "(" + " && ".join(self._generate_code(item) for item in ast.items) + ")"
            case ast_.ListOperator.OR:
                return "(" + " || ".join(self._generate_code(item) for item in ast.items) + ")"
        raise CodeGeneratorError(f"List operator {ast.op_type} is not supported in C++ code generation.")

    @_generate_code.register
    def _(self, ast: ast_.Enumeration) -> str:
        match ast.op_type:
            case ast_.CollectionOperator.SET:
                return f"std::unordered_set{{ {', '.join(self._generate_code(item) for item in ast.items)} }}"
            case ast_.CollectionOperator.RELATION | ast_.CollectionOperator.BAG | ast_.CollectionOperator.SEQUENCE:
                pair_lambda = lambda item: f"{{ {self._generate_code(item.left)}, {self._generate_code(item.right)} }}"
                return f"std::unordered_map{{ {', '.join(pair_lambda(item) for item in ast.items)} }}"
        raise CodeGeneratorError(f"Enumeration operator {ast.op_type} is not supported in C++ code generation.")

    @_generate_code.register
    def _(self, ast: ast_.Type_) -> str:
        return self._generate_code(ast.type_)

    # @_generate_code.register
    # def _(self, ast: ast_.LambdaDef) -> str: ...
    @_generate_code.register
    def _(self, ast: ast_.StructAccess) -> str:
        return f"{self._generate_code(ast.struct)}.{ast.field_name}"

    @_generate_code.register
    def _(self, ast: ast_.Call) -> str:
        return f"{self._generate_code(ast.target)}({', '.join(self._generate_code(arg) for arg in ast.args)})"

    @_generate_code.register
    def _(self, ast: ast_.Image) -> str:
        return f"{self._generate_code(ast.target)}[{self._generate_code(ast.index)}]"

    @_generate_code.register
    def _(self, ast: ast_.TypedName) -> str:
        return self._generate_code(ast.name)

    @_generate_code.register
    def _(self, ast: ast_.Assignment) -> str:
        return f"{self._generate_code(ast.target)} = {self._generate_code(ast.value)};"

    @_generate_code.register
    def _(self, ast: ast_.Return) -> str:
        return f"return {self._generate_code(ast.value)};"

    @_generate_code.register
    def _(self, ast: ast_.ControlFlowStmt) -> str:
        return f"{ast.op_type};"

    @_generate_code.register
    def _(self, ast: ast_.Statements) -> str:
        return ";\n".join(self._generate_code(stmt) for stmt in ast.items) + ";\n"

    @_generate_code.register
    def _(self, ast: ast_.Else) -> str:
        return f"else {{\n{self._generate_code(ast.body)};\n}}"

    @_generate_code.register
    def _(self, ast: ast_.If) -> str:
        return f"if ({self._generate_code(ast.condition)}) {{\n{self._generate_code(ast.body)};\n}} {self._generate_code(ast.else_body)}"

    @_generate_code.register
    def _(self, ast: ast_.Else) -> str:
        return f"else if ({self._generate_code(ast.condition)}) {{\n{self._generate_code(ast.body)};\n}} {self._generate_code(ast.else_body)}"

    @_generate_code.register
    def _(self, ast: ast_.For) -> str:
        return f"for (auto {self._generate_code(ast.iterable_names)} : {self._generate_code(ast.iterable)}) {{\n{self._generate_code(ast.body)};\n}}"

    @_generate_code.register
    def _(self, ast: ast_.While) -> str:
        return f"while ({self._generate_code(ast.condition)}) {{\n{self._generate_code(ast.body)};\n}}"

    @_generate_code.register
    def _(self, ast: ast_.RecordDef) -> str:
        fields = "; ".join(f"{self._generate_code(field.type_)} {field.name}" for field in ast.items)
        return f"struct {ast.name} {{ {fields}; }};"

    @_generate_code.register
    def _(self, ast: ast_.ProcedureDef) -> str:
        args = ", ".join(f"{self._generate_code(arg.type_)} {arg.name}" for arg in ast.args)
        return f"{self._generate_code(ast.return_type)} {ast.name}({args}) {{\n{self._generate_code(ast.body)};\n}}"

    @_generate_code.register
    def _(self, ast: ast_.Import) -> str:
        raise CodeGeneratorError(f"Import statements are not supported in C++ code generation. Got: {ast}")

    @_generate_code.register
    def _(self, ast: ast_.Start) -> str:
        return f"int main() {{\n{self._generate_code(ast.body)};\nreturn 0;\n}}"
