import os
import shutil
from functools import singledispatchmethod
from dataclasses import dataclass, field
from typing import ClassVar, Any
from loguru import logger

from src.mod.data import ast_
from src.mod.data.codegen.code_generator_base import CodeGenerator, CodeGeneratorError


@dataclass
class RustCodeGenerator(CodeGenerator):
    # ast: ast_.ASTNode
    new_symbol_table: ast_.Environment[str] = field(init=False)

    template_path: ClassVar[str] = "packages/simile_compiler/src/mod/codegen/templates/rust"

    def __post_init__(self) -> None:
        self.new_symbol_table = ast_.Environment(
            table={name: RustCodeGenerator.type_translator(typ, name) for name, typ in ast_.STARTING_ENVIRONMENT.table.items()},
        )

    @classmethod
    def type_translator(cls, simile_type: ast_.SimileType, def_name: str = "") -> str:
        """Translate Simile types to Rust types.

        Args:
            simile_type (ast_.SimileType): The Simile type to translate.
            def_name (str, optional): The name of the definition, if applicable (only used for function, enum, and struct definitions). Defaults to "".
        """
        match simile_type:
            case ast_.BaseSimileType.PosInt | ast_.BaseSimileType.Nat:
                return "Nat"
            case ast_.BaseSimileType.Int:
                return "Int"
            case ast_.BaseSimileType.Float:
                return "Float"
            case ast_.BaseSimileType.String:
                return "&str"
            case ast_.BaseSimileType.Bool:
                return "bool"
            case ast_.BaseSimileType.None_:
                return "None"
            case ast_.PairType((left, right)):
                return f"Pair<{cls.type_translator(left)}, {cls.type_translator(right)}>"
            case ast_.SetType(ast_.PairType((left, right)), _):
                return f"Relation<{cls.type_translator(left)}, {cls.type_translator(right)}>"
            case ast_.SetType(element_type, _):
                return f"HashSet<{cls.type_translator(element_type)}>"
            case ast_.StructTypeDef(fields):
                return f"struct {def_name} {{ {' '.join(f'{field[0]}: {cls.type_translator(field[1])},' for field in fields.items())} }}"
            case ast_.EnumTypeDef(element_type, _, members):
                return f"enum {def_name} {{ {', '.join(members)} }};"
            case ast_.ProcedureTypeDef(arg_types, return_type):
                logger.warning(f"Procedure types are not supported in Rust code generation (no need for type declarations). Got: {simile_type}")
                return ""
                raise ValueError(f"Procedure types are not supported in Rust code generation (no need for type declarations). Got: {simile_type}")
                # return f" {def_name}({', '.join(f'{name}: {cls.type_translator(arg)}' for name, arg in arg_types.items())}) -> {cls.type_translator(return_type)} {{}}"
            case ast_.ModuleImports(import_objects):
                raise ValueError(f"Module imports are not supported in Rust code generation yet. Got: {simile_type}")
            case ast_.TypeUnion(types):
                if len(types) == 1:
                    return cls.type_translator(next(iter(types)))
                if len(types) == 2 and ast_.BaseSimileType.None_ in types:
                    types.remove(ast_.BaseSimileType.None_)
                    return f"Option<{cls.type_translator(next(iter(types)))}>"
                raise ValueError(f"Most union types are not supported in Rust code generation. Got: {simile_type}")
            case ast_.DeferToSymbolTable(lookup_type):
                raise ValueError(f"DeferToSymbolTable types are not supported in Rust code generation (they should be resolved). Got: {simile_type} for field {def_name}")
            case ast_.GenericType(_):
                logger.warning("Skipping generic type translation for Rust code generation (should be resolved before code generation).")
                return ""
            # case ast_.BaseSimileType.Any:
            #     return "INVALID_TYPE"  # Placeholder for any type, should not be used in code generation.
        raise ValueError(f"Unsupported Simile type for Rust translation: {simile_type}")

    def generate(self) -> str:
        if self.ast._env is None:
            raise ValueError("AST environment should have been populated before code generation (see analysis module).")

        with open(f"{self.template_path}/src/main.rs", "r") as template_file:
            ret = template_file.read()

        ret += "\n//Generated code:\n\n"
        ret += "fn main() {\n"
        ret += self._generate_code(self.ast)

        ret += "\n}"

        return ret

    def build(self, target_folder_path: str = "packages/simile_compiler/build/rust") -> None:
        os.makedirs(target_folder_path, exist_ok=True)
        shutil.copytree(self.template_path, target_folder_path, dirs_exist_ok=True)

        with open(f"{target_folder_path}/src/main.rs", "w") as main_file:
            main_file.write(self.generate())

    @singledispatchmethod
    def _generate_code(self, ast: ast_.ASTNode) -> str:
        """Auxiliary function for generating code based on the type of AST node. See :func:`generate`."""
        raise NotImplementedError(f"Code generation not implemented for node type: {type(ast)} with value {ast}")

    @_generate_code.register
    def _(self, ast: ast_.Identifier) -> str:
        # should we lookup the type here?

        if ast.name.startswith("*"):
            ret = self.hash_variable_name(ast.name)
        else:
            ret = ast.name

        # loop variables are borrowed
        if self.new_symbol_table.get(ret) == "loop_identifier_variable":
            return f"*{ret}"
        return ret

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
                return "None"

        raise CodeGeneratorError(f"Unsupported literal type for Rust code generation: {type(ast)} with value {ast}")

    @_generate_code.register
    def _(self, ast: ast_.TupleIdentifier) -> str:
        return ", ".join(self._generate_code(ident) for ident in ast.items)

    @_generate_code.register
    def _(self, ast: ast_.BinaryOp) -> str:
        wrap_parens = lambda str_: f"({str_})"
        match ast.op_type:
            case ast_.BinaryOperator.IMPLIES:
                return wrap_parens(f"if {self._generate_code(ast.left)} {{ {self._generate_code(ast.right)} }} else {{true}}")
            # case ast_.BinaryOperator.REV_IMPLIES:
            #     return wrap_parens(f"if {self._generate_code(ast.right)} {{ {self._generate_code(ast.left)} }} else {{true}}")
            case ast_.BinaryOperator.EQUIVALENT | ast_.BinaryOperator.EQUAL:
                return wrap_parens(f"{self._generate_code(ast.left)} == {self._generate_code(ast.right)}")
            case ast_.BinaryOperator.NOT_EQUIVALENT | ast_.BinaryOperator.NOT_EQUAL:
                return wrap_parens(f"{self._generate_code(ast.left)} != {self._generate_code(ast.right)}")
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
            ) if ast.get_type in (ast_.BaseSimileType.Int, ast_.BaseSimileType.Float):
                left_arg = self._generate_code(ast.left)
                right_arg = self._generate_code(ast.right)

                if ast.get_type == ast_.BaseSimileType.Float:
                    left_arg = f"{left_arg} as Float"
                    right_arg = f"{right_arg} as Float"
                # elif ast.get_type == ast_.BaseSimileType.Int:
                #     left_arg = f"{left_arg} as Int"
                #     right_arg = f"{right_arg} as Int"

                return wrap_parens(f"({wrap_parens(left_arg)} {ast.op_type.to_source()} {wrap_parens(right_arg)})")
            case ast_.BinaryOperator.ADD if ast.get_type == ast_.BaseSimileType.String:
                return wrap_parens(f"{self._generate_code(ast.left)}.clone() + {self._generate_code(ast.right)}.clone()")

            # These cases should be converted into for loops by our AST optimizer...
            # case ast_.BinaryOperator.ADD if isinstance(ast.get_type, ast_.SetType) and ast_.SetType.is_sequence(ast.get_type):
            # case ast_.BinaryOperator.ADD if isinstance(ast.get_type, ast_.SetType) and ast_.SetType.is_bag(ast.get_type):

            case ast_.BinaryOperator.EXPONENT:
                left_arg = self._generate_code(ast.left)
                right_arg = self._generate_code(ast.right)
                application_function = "::pow"

                if ast.get_type == ast_.BaseSimileType.Float:
                    application_function = "Float" + application_function
                    left_arg = f"{left_arg} as Float"
                    right_arg = f"{right_arg} as Float"
                elif ast.get_type == ast_.BaseSimileType.Int:
                    application_function = "Int" + application_function
                #     left_arg = f"{left_arg} as Int"
                #     right_arg = f"{right_arg} as Int"

                return wrap_parens(f"{application_function}({wrap_parens(left_arg)}, {wrap_parens(right_arg)})")

            # Users shouldn't need to be aware of objects... Maybe remove this from the language?
            # case ast_.BinaryOperator.IS:
            # case ast_.BinaryOperator.IS_NOT:

            case ast_.BinaryOperator.IN:
                if isinstance(ast.right.get_type, ast_.SetType) and ast_.SetType.is_relation(ast.right.get_type):
                    return wrap_parens(f"{self._generate_code(ast.right)}.contains_fwd(&{self._generate_code(ast.left)})")

                return wrap_parens(f"{self._generate_code(ast.right)}.contains(&{self._generate_code(ast.left)})")
            case ast_.BinaryOperator.NOT_IN:
                if isinstance(ast.right.get_type, ast_.SetType) and ast_.SetType.is_relation(ast.right.get_type):
                    return wrap_parens(f"!{self._generate_code(ast.right)}.contains_fwd(&{self._generate_code(ast.left)})")
                return wrap_parens(f"!{self._generate_code(ast.right)}.contains(&{self._generate_code(ast.left)})")

            # These cases should be converted into for loops by our AST optimizer...
            # case ast_.BinaryOperator.UNION:
            # case ast_.BinaryOperator.INTERSECTION:
            # case ast_.BinaryOperator.DIFFERENCE:
            case ast_.BinaryOperator.SUBSET:
                return wrap_parens(f"a != b && {self._generate_code(ast.left)}.is_subset({self._generate_code(ast.right)})")
            case ast_.BinaryOperator.SUBSET_EQ:
                return wrap_parens(f"{self._generate_code(ast.left)}.is_subset({self._generate_code(ast.right)})")
            case ast_.BinaryOperator.SUPERSET:
                return wrap_parens(f"(a != b && {self._generate_code(ast.right)}.is_subset({self._generate_code(ast.left)}))")
            case ast_.BinaryOperator.SUPERSET_EQ:
                return wrap_parens(f"{self._generate_code(ast.right)}.is_subset({self._generate_code(ast.left)})")
            case ast_.BinaryOperator.NOT_SUBSET:
                return wrap_parens(f"!(a != b && {self._generate_code(ast.left)}.is_subset({self._generate_code(ast.right)}))")
            case ast_.BinaryOperator.NOT_SUBSET_EQ:
                return wrap_parens(f"!{self._generate_code(ast.left)}.is_subset({self._generate_code(ast.right)})")
            case ast_.BinaryOperator.NOT_SUPERSET:
                return wrap_parens(f"!(a != b && {self._generate_code(ast.right)}.is_subset({self._generate_code(ast.left)}))")
            case ast_.BinaryOperator.NOT_SUPERSET_EQ:
                return wrap_parens(f"!{self._generate_code(ast.right)}.is_subset({self._generate_code(ast.left)})")
            case ast_.BinaryOperator.MAPLET:
                return wrap_parens(f"({self._generate_code(ast.left)}, {self._generate_code(ast.right)})")
            # case ast_.BinaryOperator.RELATION_OVERRIDING:
            # case ast_.BinaryOperator.COMPOSITION:
            # case ast_.BinaryOperator.CARTESIAN_PRODUCT:
            case ast_.BinaryOperator.UPTO:
                return f"({self._generate_code(ast.left)}..{self._generate_code(ast.right)}).collect::<HashSet<Int>>()"
            # case ast_.BinaryOperator.DOMAIN_SUBTRACTION:
            # case ast_.BinaryOperator.DOMAIN_RESTRICTION:
            # case ast_.BinaryOperator.RANGE_SUBTRACTION:
            # case ast_.BinaryOperator.RANGE_RESTRICTION:
        raise CodeGeneratorError(f"Binary operator {ast.op_type} is not supported in Rust code generation.")

    @_generate_code.register
    def _(self, ast: ast_.RelationOp) -> str:
        raise CodeGeneratorError(f"Relation operator {ast.op_type} is not supported in Rust code generation.")

    @_generate_code.register
    def _(self, ast: ast_.UnaryOp) -> str:
        wrap_parens = lambda str_: f"({str_})"
        match ast.op_type:
            case ast_.UnaryOperator.NOT:
                return wrap_parens(f"!{self._generate_code(ast.value)}")
            case ast_.UnaryOperator.NEGATIVE:
                return wrap_parens(f"-{self._generate_code(ast.value)}")
            # case ast_.UnaryOperator.POWERSET:
            # case ast_.UnaryOperator.NONEMPTY_POWERSET:
            # case ast_.UnaryOperator.INVERSE:
        raise CodeGeneratorError(f"Unary operator {ast.op_type} is not supported in Rust code generation.")

    @_generate_code.register
    def _(self, ast: ast_.ListOp) -> str:
        wrap_parens = lambda str_: f"({str_})"
        match ast.op_type:
            case ast_.ListOperator.AND:
                return wrap_parens(" && ".join(self._generate_code(item) for item in ast.items))
            case ast_.ListOperator.OR:
                return wrap_parens(" || ".join(self._generate_code(item) for item in ast.items))
        raise CodeGeneratorError(f"List operator {ast.op_type} is not supported in Rust code generation.")

    @_generate_code.register
    def _(self, ast: ast_.Enumeration) -> str:
        match ast.op_type:
            case ast_.CollectionOperator.SET:
                return f"HashSet::from([{', '.join(self._generate_code(item) for item in ast.items)}])"
            case ast_.CollectionOperator.RELATION | ast_.CollectionOperator.BAG | ast_.CollectionOperator.SEQUENCE:
                pair_lambda = lambda item: f"({self._generate_code(item.left)}, {self._generate_code(item.right)})"
                return f"Relation::from_hash_map(HashMap::from([{', '.join(pair_lambda(item) for item in ast.items)}]))"
                # TODO optimize based on relational subtypes (ex. functions only need one direction?)
                # return f"HashMap::from([{', '.join(pair_lambda(item) for item in ast.items)}])"
        raise CodeGeneratorError(f"Enumeration operator {ast.op_type} is not supported in Rust code generation.")

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
        if ast_.SetType.is_relation(ast.target.get_type):
            return f"*{self._generate_code(ast.target)}.get_fwd({', '.join(self._generate_code(arg) for arg in ast.args)}).unwrap()"

        if isinstance(ast.target, ast_.Identifier) and ast.target.name == "print":
            return f'println!("{{:?}}", {", ".join(self._generate_code(arg) for arg in ast.args)});'
        return f"{self._generate_code(ast.target)}({', '.join(self._generate_code(arg) for arg in ast.args)})"

    @_generate_code.register
    def _(self, ast: ast_.Image) -> str:
        return f"{self._generate_code(ast.target)}[{self._generate_code(ast.index)}]"

    @_generate_code.register
    def _(self, ast: ast_.TypedName) -> str:
        return self._generate_code(ast.name)

    @_generate_code.register
    def _(self, ast: ast_.Assignment) -> str:
        target_identifier = self._generate_code(ast.target)
        if self.new_symbol_table.get(target_identifier) is not None:
            return f"{target_identifier} = {self._generate_code(ast.value)};"

        target_type = self.type_translator(ast.target.get_type)
        self.new_symbol_table.put(target_identifier, target_type)
        return f"let mut {self._generate_code(ast.target)}: {target_type} = {self._generate_code(ast.value)};"

    @_generate_code.register
    def _(self, ast: ast_.Return) -> str:
        return f"return {self._generate_code(ast.value)};"

    @_generate_code.register
    def _(self, ast: ast_.ControlFlowStmt) -> str:
        return f"{ast.op_type};"

    @_generate_code.register
    def _(self, ast: ast_.Statements) -> str:
        self.new_symbol_table = ast_.Environment(previous=self.new_symbol_table, table={})
        res = ";".join(self._generate_code(stmt) for stmt in ast.items) + ";"

        if self.new_symbol_table.previous is None:
            raise CodeGeneratorError("Symbol table should always have a previous environment (the global one). This is a bug in the code generator.")
        self.new_symbol_table = self.new_symbol_table.previous

        return res

    @_generate_code.register
    def _(self, ast: ast_.Else) -> str:
        return f"else {{{self._generate_code(ast.body)}}}"

    @_generate_code.register
    def _(self, ast: ast_.If) -> str:
        if isinstance(ast.else_body, ast_.None_):
            return f"if {self._generate_code(ast.condition)} {{{self._generate_code(ast.body)}}}"
        return f"if {self._generate_code(ast.condition)} {{{self._generate_code(ast.body)}}} {self._generate_code(ast.else_body)}"

    @_generate_code.register
    def _(self, ast: ast_.ElseIf) -> str:
        if isinstance(ast.else_body, ast_.None_):
            return f"else if {self._generate_code(ast.condition)} {{{self._generate_code(ast.body)}}}"
        return f"else if {self._generate_code(ast.condition)} {{{self._generate_code(ast.body)}}} {self._generate_code(ast.else_body)}"

    @_generate_code.register
    def _(self, ast: ast_.For) -> str:
        self.new_symbol_table = ast_.Environment(previous=self.new_symbol_table, table={})

        iterable_names = self._generate_code(ast.iterable_names)
        for name in iterable_names.split(","):
            self.new_symbol_table.put(name, "loop_identifier_variable")

        res = f"for ({iterable_names}) in {self._generate_code(ast.iterable)}.iter() {{{self._generate_code(ast.body)}}}"

        if self.new_symbol_table.previous is None:
            raise CodeGeneratorError("Symbol table should always have a previous environment (the global one). This is a bug in the code generator.")
        self.new_symbol_table = self.new_symbol_table.previous

        return res

    @_generate_code.register
    def _(self, ast: ast_.While) -> str:
        return f"while {self._generate_code(ast.condition)} {{{self._generate_code(ast.body)}}}"

    @_generate_code.register
    def _(self, ast: ast_.RecordDef) -> str:
        self.new_symbol_table.put(self._generate_code(ast.name), "struct_definition")

        fields = "; ".join(f"{self._generate_code(field.type_)} {field.name}" for field in ast.items)
        return f"struct {self._generate_code(ast.name)} {{ {fields}, }}"

    @_generate_code.register
    def _(self, ast: ast_.ProcedureDef) -> str:
        self.new_symbol_table.put(self._generate_code(ast.name), "function_definition")

        args = ", ".join(f"{arg.name}: {self._generate_code(arg.type_)}" for arg in ast.args)
        return f"fn {self._generate_code(ast.name)}({args}) -> {self._generate_code(ast.return_type)} {{{self._generate_code(ast.body)}}}"

    @_generate_code.register
    def _(self, ast: ast_.Import) -> str:
        # TODO import names should be added to the new symbol table
        raise CodeGeneratorError(f"Import statements are not supported in Rust code generation. Got: {ast}")

    @_generate_code.register
    def _(self, ast: ast_.Start) -> str:
        return self._generate_code(ast.body)
