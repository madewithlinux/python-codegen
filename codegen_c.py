import ctypes
import numpy as np
from inspect import signature
import subprocess
import tempfile
import os
import control
import traceback


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

py_c_type_map = {
    np.int: 'int32_t',
    np.int32: 'int32_t',
    np.int64: 'int64_t',
    np.uint: 'uint32_t',
    np.uint32: 'uint32_t',
    np.uint64: 'uint64_t',
    np.float: 'double',
    np.float32: 'float',
    np.float64: 'double',
    int: 'int64_t',
    float: 'double',
}


class Match:
    def __init__(self, context: 'Context', outvar):
        self.context = context
        self.outvar = outvar
        if hasattr(outvar, 'to_atoms'):
            self.outvars = outvar.to_atoms()
        else:
            self.outvars = [outvar]
        # list of (condition variable, func) to be run
        # resulting code looks like:
        # v1 = <condition code>
        # v2 = <other condition code>
        # v3;
        # ...
        # if (v1) {stuff; v3 = result}
        # else if (v2) {stuff; v3 = result}
        self.cases = []

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
        self.context.code_direct("if (0) {}\n")
        for cond, func in self.cases:
            if cond is not None:
                assert isinstance(cond, CTypeWrapper)
                self.context.code_direct(f"else if ({cond.var}) {{\n")
            else:
                self.context.code_direct(f"else {{\n")
            res_var: CTypeWrapper = func()

            if hasattr(res_var, 'to_atoms'):
                assert len(res_var.to_atoms()) == len(self.outvars)
                for lvar, rvar in zip(self.outvars, res_var.to_atoms()):
                    assert isinstance(lvar, CTypeWrapper)
                    assert isinstance(rvar, CTypeWrapper)
                    self.context.code_line(f"{lvar.var} = {rvar.var}")
                    rvar.var = lvar.var
                self.outvar.from_atoms(res_var.to_atoms())

            else:
                assert len(self.outvars) == 1
                assert isinstance(self.outvars[0], CTypeWrapper)
                self.context.code_line(f"{self.outvars[0].var} = {res_var.var}")
            self.context.code_direct("}\n")
        return self.outvar


class Context:

    def __init__(self):
        self.last_var = 0
        self._code = ''

    def label(self) -> str:
        """Search up the stack to find where we are being called from"""
        for frame in traceback.extract_stack()[::-1]:
            # find the first frame outside of this file
            if frame.filename != __file__:
                return f'#line {frame.lineno} "{frame.filename}"\n'
        else:
            return ""

    def match(self, var):
        return Match(self, var)

    def code_line(self, line: str):
        self._code += self.label()
        self._code += line + ';\n'

    def code_direct(self, code):
        self._code += code

    def literal(self, x, type):
        type = py_c_type_map[type]
        if isinstance(x, CTypeWrapper) and x.type == type:
            return x
        elif isinstance(x, CTypeWrapper):
            x = x.var
        var = self.get_var(type)
        # TODO: smarter casts?
        self._code += f'{var} = ({type})({x});\n'
        return CTypeWrapper(self, var, type)

    def cast(self, x, type):
        return self.literal(x, type)

    def get_var(self, type: str):
        var = f'v{self.last_var}'
        self._code += f'{type} {var};\n'
        self.last_var += 1
        return var

    @staticmethod
    def logical_and(a, b):
        if hasattr(a, 'logical_and'):
            return a.logical_and(b)
        else:
            return a and b

    @staticmethod
    def logical_or(a, b):
        if hasattr(a, 'logical_or'):
            return a.logical_or(b)
        else:
            return a or b


class CTypeWrapper:

    def __init__(self, context: Context, var: str, type: str):
        self.context = context
        self.var = var
        self.type = type

    def general_arithmetic(self, other: 'CTypeWrapper', op):
        if not isinstance(other, CTypeWrapper):
            # TODO: smarter casts
            other_var = f'({self.type})({other})'
        else:
            other_var = other.var
        new_var = self.context.get_var(self.type)
        self.context.code_line(f'{new_var} = {self.var} {op} {other_var}')
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
        self.context.code_line(f'{new_var} = -{self.var}')
        return CTypeWrapper(self.context, new_var, self.type)


def codegen_compile(func, datatype: str):
    """
    :param func:
    :param datatype: either 'float', 'double' or 'int'
    :return:
    """
    func_name = func.__name__
    sig = signature(func)
    # skip context parameter
    func_params = list(sig.parameters)[1:]

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
    codegen_params = [context.get_var(codegen_type) for v in func_params]
    header_params = [codegen_type + ' ' + p for p in codegen_params]

    # header
    context._code = f"""
#include <stdint.h>
{codegen_type} {func_name}({','.join(header_params)}){{"""

    params = [type_dummy_instance(context, p, codegen_type) for p in codegen_params]

    ret = func(context, *params)
    code = context._code
    code += f'return {ret.var};\n}}\n'

    fd, code_file_path = tempfile.mkstemp(prefix='codegen_', suffix='.c', text=True)
    os.close(fd)

    with open(code_file_path, 'w') as f:
        f.write(code)

    lib_file_path = code_file_path + '.so'

    try:
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
        cfunc.argtypes = [c_type for x in func_params]

    finally:
        os.unlink(code_file_path)
        os.unlink(lib_file_path)

    setattr(cfunc, 'source', code)

    return cfunc
