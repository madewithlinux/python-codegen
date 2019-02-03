from codegen_c import codegen_compile
import control
import numpy as np


def foo(x: int):
    c = control.match(x)
    c.case(x < 4)(lambda: x * 3)
    c.case(x >= 4)(lambda: x * 4)
    return c.get_result()


cfoo = codegen_compile(foo, 'int')
print(cfoo.source)

for i in range(-4, 20):
    print(i, foo(i), cfoo(i))
