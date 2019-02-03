from fixnum import FixNum
from codegen_c import codegen_compile
import control
import numpy as np


def foo(a, b):
    a = FixNum.from_int(a)
    b = FixNum.from_int(b)
    c = a * b
    return c.mantissa[0]


# print(foo(3, 4))
cfoo = codegen_compile(foo, 'int')
print(cfoo(3, 4))