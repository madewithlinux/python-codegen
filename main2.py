from ctypes import CFUNCTYPE, c_int, POINTER, c_double
import llvmlite.ir as ll
import llvmlite.binding as llvm
import numpy as np

from substitute_solver_call import solve_linear_system, LLVMCode

head = """; ModuleID = ''
target triple = "unknown-unknown-unknown"
target datalayout = ""

; Function Attrs: nounwind uwtable
define void @solve_5(double* %a, double* %b, double* %x) #0 { 
"""

tail = """ret void
}
"""

replacement = solve_linear_system(LLVMCode('%a'), LLVMCode('%b'), LLVMCode('%x'), 5).code

strmod = head + replacement + tail

# print(strmod)

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

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
    cfptr = ee.get_function_address("solve_5")
    print('test2')

    print(cfptr)
    print(target_machine.emit_assembly(llmod))

    cfunc = CFUNCTYPE(None, POINTER(c_double), POINTER(c_double), POINTER(c_double))(cfptr)

    x_sum = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    a = np.array([
        6.80, -6.05, -0.45, 8.32, -9.67,
        -2.11, -3.30, 2.58, 2.71, -5.14,
        5.66, 5.36, -2.70, 4.35, -7.26,
        5.97, -4.44, 0.27, -7.17, 6.08,
        8.23, 1.08, 9.04, 2.14, -6.87
    ])
    b = np.array([4.02, 6.19, -8.22, -7.57, -3.03])
    x = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    iter = 1000000
    for i in range(iter//100):

        cfunc(
            a.ctypes.data_as(POINTER(c_double)),
            b.ctypes.data_as(POINTER(c_double)),
            x.ctypes.data_as(POINTER(c_double))
        )
        x_sum += x
        print(i)
    print(x_sum)
    print(x_sum * 100)

