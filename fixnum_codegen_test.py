from fixnum import FixNum
from codegen_c import codegen_compile
import control
import numpy as np


def foo(context: control.Context, a, b):
    a = FixNum.from_int(context, a)
    b = FixNum.from_int(context, b)
    c = a * b
    return c.mantissa[0]


# print(foo(3, 4))
cfoo = codegen_compile(foo, 'int')
print(cfoo(3, 4))
print(foo(control.context, 3, 4))
