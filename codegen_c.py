import ctypes
import numpy as np
from inspect import signature
import subprocess
import tempfile
import os


def logical_and(a, b):
    if isinstance(a, CTypeWrapper):
        return a.logical_and(b)
    else:
        return a and b


def logical_or(a, b):
    if isinstance(a, CTypeWrapper):
        return a.logical_or(b)
    else:
        return a or b


type_double = 'double'
type_int = 'int64_t'
type_uint = 'uint64_t'


class Match:
    def __init__(self, context: 'Context'):
        self.context = context
        # list of (condition variable, func) to be run
        # resulting code looks like:
        # v1 = <condition code>
        # v2 = <other condition code>
        # v3;
        # ...
        # if (v1) {stuff; v3 = result}
        # else if (v2) {stuff; v3 = result}
        self.cases = []
        # TODO: types
        self.type = 'int'
        self.result_var = context.get_var(self.type)

    def case(self, condition: str):
        # no parameters, I guess?
        def foo(func):
            self.cases.append((condition, func))

        return foo

    def default(self):
        def foo(func):
            self.cases.append((None, func))

        return foo

    def get_result(self):
        self.context.code += "if (0) {}\n"
        for cond, func in self.cases:
            assert isinstance(cond, CTypeWrapper)
            self.context.code += f"else if ({cond.var}) {{\n"
            res_var: CTypeWrapper = func()
            self.context.code += f"{self.result_var} = {res_var.var};\n"
            self.context.code += "}\n"
        return CTypeWrapper(self.context, self.result_var, self.type)


class Context:

    def __init__(self):
        self.last_var = 0
        self.code = ''
        self.codegen_match = Match(self)

    def get_var(self, type: str):
        var = f'v{self.last_var}'
        self.code += f'{type} {var};\n'
        self.last_var += 1
        return var


class CTypeWrapper:

    def __init__(self, context: Context, var: str, type: str):
        self.context = context
        self.var = var
        self.type = type
        self.codegen_match = Match(self.context)

    def general_arithmetic(self, other: 'CTypeWrapper', op):
        if not isinstance(other, CTypeWrapper):
            other_var = f'({self.type})({other})'
        else:
            other_var = other.var
        new_var = self.context.get_var(self.type)
        self.context.code += f'{new_var} = {self.var} {op} {other_var};\n'
        return CTypeWrapper(self.context, new_var, self.type)

    def __add__(self, other: 'CTypeWrapper'):
        return self.general_arithmetic(other, '+')

    def __sub__(self, other):
        return self.general_arithmetic(other, '-')

    def __mul__(self, other):
        return self.general_arithmetic(other, '*')

    def __truediv__(self, other):
        return self.general_arithmetic(other, '/')

    def __gt__(self, other):
        return self.general_arithmetic(other, '>')

    def __ge__(self, other):
        return self.general_arithmetic(other, '>=')

    def __lt__(self, other):
        return self.general_arithmetic(other, '<')

    def __le__(self, other):
        return self.general_arithmetic(other, '<=')

    def __eq__(self, other):
        return self.general_arithmetic(other, '==')

    def __lshift__(self, other):
        return self.general_arithmetic(other, '<<')

    def __rshift__(self, other):
        return self.general_arithmetic(other, '>>')

    def __and__(self, other):
        return self.general_arithmetic(other, '&')

    def __or__(self, other):
        return self.general_arithmetic(other, '|')

    def __xor__(self, other):
        return self.general_arithmetic(other, '^')

    def logical_and(self, other):
        return self.general_arithmetic(other, '&&')

    def logical_or(self, other):
        return self.general_arithmetic(other, '||')

    def __neg__(self):
        new_var = self.context.get_var(self.type)
        self.context.code += f'{new_var} = -{self.var};\n'
        return CTypeWrapper(self.context, new_var, self.type)


def codegen_compile(func, datatype: str):
    """
    :param func:
    :param datatype: either 'float', 'double' or 'int'
    :return:
    """
    func_name = func.__name__
    sig = signature(func)

    if datatype.startswith('int'):
        c_type = ctypes.c_int64
        codegen_type = type_int
    elif datatype.startswith('uint'):
        c_type = ctypes.c_uint64
        codegen_type = type_uint
    elif datatype.startswith('float') or datatype == 'double':
        c_type = ctypes.c_double
        codegen_type = type_double
    else:
        return None
    type_dummy_instance = CTypeWrapper

    context = Context()
    codegen_params = [context.get_var(codegen_type) for v in sig.parameters]
    header_params = [codegen_type + ' ' + p for p in codegen_params]

    # header
    context.code = f"""
#include <stdint.h>
{codegen_type} {func_name}({','.join(header_params)}){{"""

    params = [type_dummy_instance(context, p, codegen_type) for p in codegen_params]

    ret = func(*params)
    code = context.code
    code += f'return {ret.var};\n}}\n'

    fd, code_file_path = tempfile.mkstemp(suffix='.c', text=True)
    os.close(fd)

    with open(code_file_path, 'w') as f:
        f.write(code)

    lib_file_path = code_file_path + '.so'
    subprocess.check_call([
        'gcc',
        code_file_path,
        '-o', lib_file_path,
        '-fPIC',
        '-shared',
        '-O3',
    ])

    lib = ctypes.CDLL(lib_file_path)
    cfunc = lib[func_name]
    cfunc.restype = c_type
    cfunc.argtypes = [c_type for x in sig.parameters]

    os.unlink(code_file_path)
    os.unlink(lib_file_path)

    setattr(cfunc, 'source', code)

    return cfunc
