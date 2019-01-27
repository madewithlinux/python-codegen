from ctypes import CFUNCTYPE, c_int, POINTER
import llvmlite.ir as ll
import llvmlite.binding as llvm
import numpy as np

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

fntype = ll.FunctionType(ll.IntType(32), [ll.IntType(32), ll.IntType(32)])

module = ll.Module()

func = ll.Function(module, fntype, name='foo')
bb_entry = func.append_basic_block()

builder = ll.IRBuilder()
builder.position_at_end(bb_entry)

stackint = builder.alloca(ll.IntType(32))
builder.store(ll.Constant(stackint.type.pointee, 123), stackint)
myint = builder.load(stackint)

addinstr = builder.add(func.args[0], func.args[1])
mulinstr = builder.mul(addinstr, ll.Constant(ll.IntType(32), 123))
pred = builder.icmp_signed('<', addinstr, mulinstr)
builder.ret(mulinstr)

bb_block = func.append_basic_block()
builder.position_at_end(bb_block)

bb_exit = func.append_basic_block()

pred = builder.trunc(addinstr, ll.IntType(1))
builder.cbranch(pred, bb_block, bb_exit)

builder.position_at_end(bb_exit)
builder.ret(myint)

strmod = str(module)
print(strmod)
llmod = llvm.parse_assembly(strmod)

pmb = llvm.create_pass_manager_builder()
pmb.opt_level = 2
pm = llvm.create_module_pass_manager()
pmb.populate(pm)

pm.run(llmod)

target_machine = llvm.Target.from_default_triple().create_target_machine()
with llvm.create_mcjit_compiler(llmod, target_machine) as ee:
    ee.finalize_object()
    print('test')
    cfptr = ee.get_function_address("foo")
    print('test2')

    print(cfptr)
    print(target_machine.emit_assembly(llmod))

    cfunc = CFUNCTYPE(c_int, c_int, c_int)(cfptr)
    # A = np.arange(10, dtype=np.int32)
    # res = cfunc(A.ctypes.data_as(POINTER(c_int)), A.size)
    res = cfunc(2, 7)
    print('res1', res)
    print('res2', (2 + 7) * 123)
