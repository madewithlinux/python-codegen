# from codegen_llvm import codegen
from codegen.codegen_llvm_builder import codegen_compile

# def foo(a, b, c, d) -> float:
#     return a + b / c * d + a * (b + d)

iter = 1000
r = 3.8


def foo(x: float):
    for i in range(iter):
        x = x * (-x + 1) * r
    return x


# code = codegen(foo)
# print(code)
#
# llmod = llvm.parse_assembly(code)
#
# pmb = llvm.create_pass_manager_builder()
# pmb.opt_level = 2
# pm = llvm.create_module_pass_manager()
# pmb.populate(pm)
#
# pm.run(llmod)
#
# target_machine = llvm.Target.from_default_triple().create_target_machine()
# # with llvm.create_mcjit_compiler(llmod, target_machine) as ee:
# #     ee.finalize_object()
# #     print('test')
# #     cfptr = ee.get_function_address("foo")
# #     print('test2', cfptr)
# #
# #     print(target_machine.emit_assembly(llmod))
# #
# #     cfoo = CFUNCTYPE(c_double, c_double)(cfptr)
# #     print(cfoo)
# #     print(cfoo(0.5))
# #     print(foo(0.5))
# #     # cfoo = CFUNCTYPE(c_double, c_double, c_double, c_double, c_double)(cfptr)
# #     # print(cfoo(1.0, 2.0, 3.0, 4.0))
# #     # print(foo(1.0, 2.0, 3.0, 4.0))
#
# ee = llvm.create_mcjit_compiler(llmod, target_machine)
# ee.finalize_object()
# print('test')
# cfptr = ee.get_function_address("foo")
# print('test2', cfptr)
#
# print(target_machine.emit_assembly(llmod))

cfoo = codegen_compile(foo, 'double')
print(cfoo)
print(cfoo(0.5))
print(foo(0.5))
