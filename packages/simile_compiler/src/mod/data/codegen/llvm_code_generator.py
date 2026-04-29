from functools import singledispatchmethod
from dataclasses import dataclass, field
from typing import ClassVar

from llvmlite import ir  # type: ignore
import llvmlite.binding as llvm  # type: ignore

from src.mod.data import ast_


@dataclass
class LLVMCodeGenerator:

    env: dict[str, ast_.Environment] = field(default=None, init=False, repr=False)


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
                return ir.PointerType(ir.IntType(8))
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
                return ir.SetType(cls.simile_to_llvm_type(element_type))
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

    def generate_llvm_code(self, node: ast_.ASTNode) -> ir.Value:
        """
        Generate LLVM IR code for a given AST node.

        Args:
            node: The AST node to generate code for.

        Returns:
            An LLVM IR value representing the generated code.
        """
        # llvm.initialize()
        # llvm.initialize_native_target()
        # llvm.initialize_native_asmprinter()

        return self._generate_llvm_code(node)

    @singledispatchmethod
    def _generate_llvm_code(self, node: ast_.ASTNode):
        """Auxiliary function for generating LLVM code based on the type of AST node. See :func:`generate_llvm_code`."""
        raise NotImplementedError(f"Code generation not implemented for node type: {type(node)} with value {node}")

    @_generate_llvm_code.register
    def _(self, node: ast_.Identifier): ...
