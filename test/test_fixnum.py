import pytest
import numpy as np
import control
from control import Context
from codegen.codegen_c import codegen_compile
from codegen.fixnum import FixNum
import random
import logging

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
