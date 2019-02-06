import pytest
import numpy as np
import control
from control import Context
from codegen.codegen_c import codegen_compile

import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()


def foo(t, context: Context, a, b, c, d, e):
    x1 = a + b
    x2 = c - d
    # TODO division
    # x3 = e // context.cast(4, t)
    x3 = e
    x4 = x1 * x2
    x5 = x3 * context.cast(123.456, t) + x4
    return x5


types = [
    np.int,
    np.int32,
    np.int64,
    np.uint,
    np.uint32,
    np.uint64,
    np.float,
    np.float32,
    np.float64,
    int,
    float,
]

# list of pairs of (in, type)
testdata = [
    ((a, b, c, d, e), t)
    for a in [612.5904107398447,
              1084.1972329537664,
              # -741.746654750965,
              927.8962181717923]
    for b in [1.4880169140058825,
              # 6.807036959760545,
              # 4.926786534279249,
              5.906097334131645]
    for c in [737869570.7930409,
              # 583832518.7744356,
              # -356474702.7810973,
              821624371.196466]
    for d in [528776.9772536517,
              # 8605896.874739313,
              # 8626590.06360328,
              -321169.852095944]
    for e in [755139.5311161152,
              # 324924.8998622409,
              # 193921.33440300566,
              -158363.92917228653]
    for t in types
]


def compile_foo(t):
    def foo2(context, a, b, c, d, e):
        return foo(t    , context, a, b, c, d, e)

    cfoo = codegen_compile(foo2, t)
    return cfoo


cfoos = {
    t: compile_foo(t)
    for t in types
}


@pytest.mark.parametrize("inputs, t", testdata)
def test_arithmetic(inputs, t):
    inputs = [t(i) for i in inputs]
    expected = foo(t, control.default_context, *inputs)
    cfoo = cfoos[t]
    actual = cfoo(*inputs)
    assert actual == expected
