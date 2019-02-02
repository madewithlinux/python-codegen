import ctypes
import numpy as np
from inspect import signature
import subprocess
import tempfile
import os

type_double = 'double'


class Context:
    def __init__(self):
        self.last_var = 0
        self.code = ''

    def get_var(self, type: str):
        var = f'v{self.last_var}'
        self.code += f'{type} {var};\n'
        self.last_var += 1
        return var


class CDouble:
    def __init__(self, context: Context, var: str):
        self.context = context
        self.var = var
        self.type = type_double

    def general_arithmetic(self, other: 'CDouble', op):
        other_var = ''
        if not isinstance(other, CDouble):
            other_var = f'(double)({float(other)})'
        else:
            other_var = other.var
        new_var = self.context.get_var(self.type)
        self.context.code += f'{new_var} = {self.var} {op} {other_var};\n'
        return CDouble(self.context, new_var)

    def __add__(self, other: 'CDouble'):
        return self.general_arithmetic(other, '+')

    def __sub__(self, other):
        return self.general_arithmetic(other, '-')

    def __mul__(self, other):
        return self.general_arithmetic(other, '*')

    def __truediv__(self, other):
        return self.general_arithmetic(other, '/')

    def __neg__(self):
        new_var = self.context.get_var(self.type)
        self.context.code += f'{new_var} = -{self.var};\n'
        return CDouble(self.context, new_var)


def codegen_compile(func, datatype: str):
    """
    :param func:
    :param datatype: either 'float', 'double' or 'int'
    :return:
    """
    func_name = func.__name__
    sig = signature(func)

    c_type = ctypes.c_double
    codegen_type = type_double
    type_dummy_instance = CDouble

    context = Context()
    codegen_params = [context.get_var(codegen_type) for v in sig.parameters]
    header_params = [codegen_type + ' ' + p for p in codegen_params]
    # header
    context.code = f"""
    {codegen_type} {func_name}({','.join(header_params)}){{"""
    params = [type_dummy_instance(context, p) for p in codegen_params]

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

    return cfunc
