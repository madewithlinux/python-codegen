from codegen.codegen_c import codegen_compile
import numpy as np

# def foo(a, b, c, d) -> float:
#     return a + b / c * d + a * (b + d)

iter = 500
r = 3.8


def foo(x: float):
    for i in range(iter):
        x = x * (-x + 1) * r
    return x


cfoo = codegen_compile(foo, 'double')
print(foo)
print(cfoo)
print(cfoo(0.5))
print(foo(0.5))
# print(cfoo.source)

##########################

iter = 1000
r = 3


def foo(x: int):
    for i in range(iter):
        #     x += x * r
        x = x * (-x + 1) * r
    return x


cfoo = codegen_compile(foo, 'int')
print(cfoo)
print(cfoo(17))
print(foo(np.int64(17)))
