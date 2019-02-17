import pytest
from codegen import control
from codegen.codegen_c import codegen_compile
from codegen.fixnum import FixNum

# TODO real test when we can return a fixnum from codegen function

int_inputs = [
    (a, b)
    for a in range(-10, 10)
    for b in range(-10, 10)
]


def multiply(context: control.Context, a, b):
    a = FixNum.from_int(context, a)
    b = FixNum.from_int(context, b)
    c = a * b
    return c.mantissa[0]


cmultiply = codegen_compile(multiply, 'int')


@pytest.mark.parametrize("a,b", int_inputs)
def test_fixnum_multiply(a, b):
    expected = multiply(control.default_context, a, b)
    actual = cmultiply(a, b)
    assert expected == actual


def add(context: control.Context, a, b):
    a = FixNum.from_int(context, a)
    b = FixNum.from_int(context, b)
    c = a + b
    return c.mantissa[0]


cadd = codegen_compile(add, 'int')


@pytest.mark.parametrize("a,b", int_inputs)
def test_fixnum_add(a, b):
    expected = add(control.default_context, a, b)
    actual = cadd(a, b)
    assert expected == actual


## test fixnum from_float
xs = [
    1.234,
    10001.111,
    0.001234,
]
@pytest.mark.parametrize("x", xs)
def test_fixnum_from_float(x: float):
    def fixnum_from_float(context: control.Context, i: int):
        f = FixNum.from_float_literal(context, x)
        return f.mantissa[0] + f.mantissa[1] + f.mantissa[2] + f.mantissa[3]

    cfoo = codegen_compile(fixnum_from_float, 'int')
    expected = fixnum_from_float(control.default_context, 0)
    actual = cfoo(0)
    assert expected == actual


@pytest.mark.parametrize("x", xs)
def test_fixnum_to_float(x: float):
    def fixnum_to_float(context: control.Context, i: int):
        f = FixNum.from_float_literal(context, x)
        return f.to_float_imprecise()

    cfoo = codegen_compile(fixnum_to_float, 'double')
    expected = fixnum_to_float(control.default_context, 0)
    actual = cfoo(0)
    assert expected == actual

