from codegen_c import codegen_compile


# def foo(a, b, c, d) -> float:
#     return a + b / c * d + a * (b + d)

iter = 5
r = 3.8


def foo(x: float):
    for i in range(iter):
        x = x * (-x + 1) * r
    return x


cfoo = codegen_compile(foo, 'double')
print(cfoo)
# print(cfoo)
# print(cfoo(0.5))
# print(foo(0.5))
