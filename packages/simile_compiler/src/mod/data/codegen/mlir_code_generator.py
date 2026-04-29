from functools import singledispatchmethod
from dataclasses import dataclass, field
from typing import ClassVar

from mlir import ir

from src.mod.data import ast_


@dataclass
class MLIRCodeGenerator:
    ast: ast_.ASTNode

    @property
    def env(self) -> ast_.SymbolTableEnvironment:
        assert self.ast._env is not None, "AST environment should be populated before code generation (run analysis.populate_ast_environments)."
        return self.ast._env


    @classmethod
    def simile_to_llvm_type(cls, simile_type: ast_.SimileType) -> ir.Type:
        match simile_type:
            case ast_.BaseSimileType.PosInt | ast_.BaseSimileType.Nat:
                return ir.IntType(64)
            case ast_.BaseSimileType.Int:
                return ir.IntType(64)
            case ast_.BaseSimileType.Float:
                return ir.DoubleType()
            case ast_.BaseSimileType.String:

            case ast_.BaseSimileType.Bool:
                return ir.IntType(1)
            case ast_.BaseSimileType.None_:
                return ir.VoidType()
            case ast_.PairType(left, right):
                return ir.LiteralStructType(
                    [
                        cls.simile_to_llvm_type(left),
                        cls.simile_to_llvm_type(right),
                    ]
                )
            case ast_.SetType(element_type, relation_subtype):
            case ast_.StructTypeDef(fields):
                return ir.IdentifiedStructType().set_body(*[cls.simile_to_llvm_type(field) for field in fields.values()])
            case ast_.EnumTypeDef(members):
                return ir.MetaDataType
            case ast_.ProcedureTypeDef(arg_types, return_type):
                return ir.FunctionType(
                    cls.simile_to_llvm_type(return_type),
                    [cls.simile_to_llvm_type(arg) for arg in arg_types],
                )
            case ast_.ModuleImports(import_objects):
            case ast_.TypeUnion(types):
                raise ValueError(f"Union types are not supported in LLVM code generation. Got: {simile_type}")
            case ast_.DeferToSymbolTable(lookup_type):
                raise ValueError(f"DeferToSymbolTable types are not supported in LLVM code generation (they should be resolved). Got: {simile_type}")

        raise ValueError(f"Unsupported Simile type for LLVM conversion: {simile_type}")

    def generate(self) -> ir.Value:
        if self.ast is None:
            raise ValueError("No AST provided for code generation.")

        return self._generate_code(self.ast)

    @singledispatchmethod
    def _generate_code(self, node: ast_.ASTNode):
        """Auxiliary function for generating LLVM code based on the type of AST node. See :func:`generate_llvm_code`."""
        raise NotImplementedError(f"Code generation not implemented for node type: {type(node)} with value {node}")

    @_generate_code.register
    def _(self, node: ast_.Identifier): ...

