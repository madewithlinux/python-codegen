from codegen.codegen_c import codegen_compile
import control
import numpy as np


def foo(context: control.Context, x: int):
    c = context.match(x)
    c.case(x < context.literal(4, np.int))(lambda: x * 3)
    c.case(x >= 4)(lambda: x * context.literal(4, np.int))
    return c.get_result()


cfoo = codegen_compile(foo, 'int')
print(cfoo.source)

for i in range(-4, 20):
    print(i, foo(control.default_context, i), cfoo(i))
