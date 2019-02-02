from ctypes import CFUNCTYPE, c_int64, POINTER, c_double
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


class LLVMDouble:
    def __init__(self, context: Context, instruction: ll.Instruction):
        self.context = context
        self.instruction = instruction

    def general_arithmetic(self, other: 'LLVMDouble', inst_op, f_op, i_op):
        if not isinstance(other, LLVMDouble):
            other = ll.values.Constant(ll.DoubleType(), float(other))
            instr = getattr(self.context.builder, inst_op)(self.instruction, other)
        else:
            instr = getattr(self.context.builder, inst_op)(self.instruction, other.instruction)
        return LLVMDouble(self.context, instr)

    def __add__(self, other_llvcode: 'LLVMDouble'):
        return self.general_arithmetic(other_llvcode, 'fadd', 'fadd', 'fadd')

    def __sub__(self, other_llvcode):
        return self.general_arithmetic(other_llvcode, 'fsub', 'fsub', 'fsub')

    def __mul__(self, other_llvcode):
        return self.general_arithmetic(other_llvcode, 'fmul', 'fmul', 'fmul')

    def __truediv__(self, other_llvcode):
        return self.general_arithmetic(other_llvcode, 'fdiv', 'fdiv', 'fdiv')

    def __neg__(self):
        instr = self.context.builder.fsub(ll.values.Constant(ll.DoubleType(), 0.0), self.instruction)
        return LLVMDouble(self.context, instr)


class LLVMInt64:
    def __init__(self, context: Context, instruction: ll.Instruction):
        self.context = context
        self.instruction = instruction

    def general_arithmetic(self, other: 'LLVMInt64', op):
        if not isinstance(other, LLVMInt64):
            other = ll.values.Constant(ll.IntType(64), int(other))
            instr = getattr(self.context.builder, op)(self.instruction, other)
        else:
            instr = getattr(self.context.builder, op)(self.instruction, other.instruction)
        return LLVMInt64(self.context, instr)

    def __add__(self, other_llvcode: 'LLVMInt64'):
        return self.general_arithmetic(other_llvcode, 'add')

    def __sub__(self, other_llvcode):
        return self.general_arithmetic(other_llvcode, 'sub')

    def __mul__(self, other_llvcode):
        return self.general_arithmetic(other_llvcode, 'mul')

    def __truediv__(self, other_llvcode):
        return self.general_arithmetic(other_llvcode, 'div')

    def __neg__(self):
        instr = getattr(self.context.builder, 'neg')(self.instruction)
        return LLVMInt64(self.context, instr)


param_names = [chr(i) for i in range(ord('a'), ord('z') + 1)]

target_machine = llvm.Target.from_default_triple().create_target_machine()


def codegen_compile(func, datatype):
    """
    :param func:
    :param datatype: either 'float', 'double' or 'int'
    :return:
    """
    func_name = func.__name__
    sig = signature(func)

    if datatype == 'int':
        llvm_type = ll.IntType(64)
        type_dummy_instance = LLVMInt64
        c_type = c_int64
    elif datatype in ['float', 'double']:
        llvm_type = ll.DoubleType()
        type_dummy_instance = LLVMDouble
        c_type = c_double
    else:
        return None

    llvm_param_types = [llvm_type for c in param_names[:len(sig.parameters)]]
    fntype = ll.FunctionType(llvm_type, llvm_param_types)
    module = ll.Module()
    llvm_func = ll.Function(module, fntype, name=func_name)
    bb_entry = llvm_func.append_basic_block()
    builder = ll.IRBuilder()
    builder.position_at_end(bb_entry)

    context = Context(builder)
    params = [type_dummy_instance(context, arg) for arg in llvm_func.args]

    ret = func(*params)
    context.builder.ret(ret.instruction)

    code = str(module)

    llmod = llvm.parse_assembly(code)

    pmb = llvm.create_pass_manager_builder()
    pmb.opt_level = 2
    pm = llvm.create_module_pass_manager()
    pmb.populate(pm)

    pm.run(llmod)

    ee = llvm.create_mcjit_compiler(llmod, target_machine)
    ee.finalize_object()
    cfptr = ee.get_function_address(func_name)

    cfunc = CFUNCTYPE(c_type, *[c_type for c in llvm_param_types])(cfptr)
    # keep the reference alive
    # (this is probably an ugly hack? but whatever)
    cfunc.execution_engine = ee
    cfunc.target_asm = target_machine.emit_assembly(llmod)
    cfunc.llvm_code = code
    return cfunc
