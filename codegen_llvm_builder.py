from ctypes import CFUNCTYPE, c_int, POINTER
import llvmlite.ir as ll
import llvmlite.binding as llvm
import numpy as np
from inspect import signature

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


class Context:
    def __init__(self, builder: ll.IRBuilder):
        self.builder = builder


class LLVMCode:
    def __init__(self, context: Context, instruction: ll.Instruction):
        self.context = context
        self.instruction = instruction

    def general_arithmetics(self, other: 'LLVMCode', inst_op, f_op, i_op):
        if not isinstance(other, LLVMCode):
            other = ll.values.Constant(ll.DoubleType(), float(other))
            instr = getattr(self.context.builder, inst_op)(self.instruction, other)
        else:
            instr = getattr(self.context.builder, inst_op)(self.instruction, other.instruction)
        return LLVMCode(self.context, instr)

    def __add__(self, other_llvcode: 'LLVMCode'):
        return self.general_arithmetics(other_llvcode, 'fadd', 'fadd', 'fadd')

    def __sub__(self, other_llvcode):
        return self.general_arithmetics(other_llvcode, 'fsub', 'fsub', 'fsub')

    def __mul__(self, other_llvcode):
        return self.general_arithmetics(other_llvcode, 'fmul', 'fmul', 'fmul')

    def __truediv__(self, other_llvcode):
        return self.general_arithmetics(other_llvcode, 'fdiv', 'fdiv', 'fdiv')

    def __neg__(self):
        instr = self.context.builder.fsub(ll.values.Constant(ll.DoubleType(), 0.0), self.instruction)
        return LLVMCode(self.context, instr)


param_names = [chr(i) for i in range(ord('a'), ord('z') + 1)]


def codegen(func):
    func_name = func.__name__
    sig = signature(func)

    param_types = [ll.DoubleType() for c in param_names[:len(sig.parameters)]]
    fntype = ll.FunctionType(ll.DoubleType(), param_types)
    module = ll.Module()
    llvm_func = ll.Function(module, fntype, name=func_name)
    bb_entry = llvm_func.append_basic_block()
    builder = ll.IRBuilder()
    builder.position_at_end(bb_entry)

    context = Context(builder)
    params = [LLVMCode(context, arg) for arg in llvm_func.args]

    ret: LLVMCode = func(*params)
    context.builder.ret(ret.instruction)
    return str(module)
