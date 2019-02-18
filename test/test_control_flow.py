import pytest
from codegen import control
from codegen.control import Context
from codegen.codegen_c import codegen_compile
import random

import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

lookup_table = [
    0.3071436851788777,
    0.6950476458827405,
    0.9773769628193737,
    0.6133104845820258,
    0.4433494887714803,
    0.23003275463253858,
    0.4905437080525886,
    0.3398345802613617,
    0.2941169205951658,
    0.27113275224630884,
    0.1397476148556306,
]


def lookup(context: Context, x: float):
    out = context.literal(0, float)
    m = context.match(out)
    table_size = context.literal(len(lookup_table), float)
    m.case(x <= 0)(lambda: context.literal(lookup_table[0], float))
    for i, v in enumerate(lookup_table):
        i = context.literal(i, float)
        # must make parameter to capture v by value
        m.case(x * table_size > i)(lambda v=v: context.literal(v, float))
    m.default()(lambda: context.literal(lookup_table[-1], float))
    log.debug(m.get_result())
    return m.get_result()


clookup = codegen_compile(lookup, float, float)


@pytest.mark.parametrize("x", [random.random() for x in range(2 * len(lookup_table))])
def test_arithmetic(x):
    expected = lookup(control.default_context, x)
    actual = clookup(x)
    assert actual == expected

