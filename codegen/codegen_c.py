from __future__ import annotations

import ctypes
from dataclasses import dataclass
import numpy as np
from inspect import signature
import subprocess
import tempfile
import os
import typing
import traceback
from typing import List
import codegen.control as control


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


@dataclass
class _TypeInfo:
    codegen_type: str
    np_type: typing.Type[np.number]
    ctype: object
    py_type: typing.Union[typing.Type[int], typing.Type[float]]


_known_types = [
    _TypeInfo('int32_t', np.int32, ctypes.c_int, int),
    _TypeInfo('int64_t', np.int64, ctypes.c_long, int),
    _TypeInfo('uint32_t', np.uint32, ctypes.c_uint, int),
    _TypeInfo('uint64_t', np.uint64, ctypes.c_ulong, int),
    _TypeInfo('float', np.float32, ctypes.c_float, float),
    _TypeInfo('double', np.float64, ctypes.c_double, float),
]


def type_info(*,
              codegen_type: str = None,
              np_type: typing.Type[np.number] = None,
              ctype: object = None,
              py_type: typing.Union[typing.Type[int], typing.Type[float]] = None) -> _TypeInfo:
    # must specify exactly one query parameter
    assert sum([int(codegen_type is not None),
                int(np_type is not None),
                int(ctype is not None),
                int(py_type is not None)]) == 1
    # python type overrides
    if py_type is not None:
        if py_type == int:
            np_type = np.int64
        elif py_type == float:
            np_type = np.float64
        else:
            raise ValueError(f'bad py_type: {py_type}')
    # TODO use dicts for lookup maybe
    for t in _known_types:
        if t.codegen_type == codegen_type: return t
        if t.np_type == np_type: return t
        if t.ctype == ctype: return t
    else:
        raise ValueError(f'no match found for inputs {codegen_type} {np_type} {ctype} {py_type}')


def normalize_to_type_info(t) -> _TypeInfo:
    if t == 'int':
        return type_info(np_type=np.int64)
    if t == 'uint':
        return type_info(np_type=np.uint64)
    if t == int or t == float:
        return type_info(py_type=t)
    if isinstance(t, str):
        return type_info(codegen_type=t)
    if issubclass(t, np.number):
        return type_info(np_type=t)
    return type_info(ctype=t)


class Match:
    def __init__(self, context: Context, outvar):
        self.context = context
        self.outvar = outvar
        if hasattr(outvar, 'to_atoms'):
            outvars: List[CTypeWrapper] = outvar.to_atoms()
            self.outvars = [CTypeWrapper(context, context.get_varname(v.type), v.type) for v in outvars]
        else:
            assert isinstance(outvar, CTypeWrapper)
            self.outvars = [CTypeWrapper(context, context.get_varname(outvar.type), outvar.type)]
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
        self.context.label('condition')
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
                self.outvar = self.outvar.from_atoms(self.outvars)

            else:
                assert len(self.outvars) == 1
                assert isinstance(self.outvars[0], CTypeWrapper)
                self.context.code_line(f"{self.outvars[0].var} = {res_var.var}")
                self.outvar = self.outvars[0]
            self.context.code_direct("}\n")
        return self.outvar


class Context(control.Context):

    def __init__(self):
        self.last_var = 0
        self.last_tag = 0
        self._code = ''
        self._debug_filename_log = False
        # self._debug_filename_log = True

    def label(self, tag: str = ''):
        self._code += self._label(tag)

    def _label(self, tag: str = '') -> str:
        """Search up the stack to find where we are being called from"""
        for frame in traceback.extract_stack()[::-1]:
            # find the first frame outside of this file
            if frame.filename != __file__:
                self.last_tag += 1
                if self._debug_filename_log:
                    return f'puts("// {frame.filename}:{frame.lineno} {tag} {self.last_tag}");\n'
                else:
                    return f'#line {frame.lineno} "{frame.filename}"\n'
        else:
            return ""

    def match(self, var):
        return Match(self, var)

    def code_line(self, line: str):
        self._code += self._label()
        self._code += line + ';\n'

    def code_direct(self, code):
        self._code += code

    def literal(self, x, type):
        self.label('literal')
        # type = _py_codegen_type_map[type]
        type = normalize_to_type_info(type).codegen_type
        if isinstance(x, CTypeWrapper) and x.type == type:
            return x
        elif isinstance(x, CTypeWrapper):
            x = x.var
        var = self.get_varname(type)
        # TODO: smarter casts?
        self._code += f'{var} = ({type})({x});\n'
        return CTypeWrapper(self, var, type)

    def cast(self, x, type):
        self.label('cast')
        return self.literal(x, type)

    def get_varname(self, t: _TypeInfo) -> str:
        if not isinstance(t, _TypeInfo):
            t = normalize_to_type_info(t)
        self.label('get_var')
        var = f'v{self.last_var}'
        self._code += f'{t.codegen_type} {var};\n'
        self.last_var += 1
        return var

    def get_var_wrapper(self, t: _TypeInfo) -> CTypeWrapper:
        varname = self.get_varname(t)
        wrapper = CTypeWrapper(self, varname, t.codegen_type)
        return wrapper

    def logical_and(self, a, b):
        if hasattr(a, 'logical_and'):
            return a.logical_and(b)
        else:
            return a and b

    def logical_or(self, a, b):
        if hasattr(a, 'logical_or'):
            return a.logical_or(b)
        else:
            return a or b


class CTypeWrapper:

    def __init__(self, context: Context, var: str, type: str):
        self.context = context
        self.var = var
        # TODO changet type to TypeInfo
        self.type = type

    def general_arithmetic(self, other: CTypeWrapper, op):
        if not isinstance(other, CTypeWrapper):
            # TODO: smarter casts
            other_var = f'({self.type})({other})'
        else:
            other_var = other.var
        new_var = self.context.get_varname(self.type)
        self.context.code_line(f'{new_var} = {self.var} {op} {other_var}')
        return CTypeWrapper(self.context, new_var, self.type)

    def __add__(self, other: CTypeWrapper):
        return self.general_arithmetic(other, '+')

    def __sub__(self, other):
        return self.general_arithmetic(other, '-')

    def __mul__(self, other):
        return self.general_arithmetic(other, '*')

    def __floordiv__(self, other):
        return self.general_arithmetic(other, '/')

    # TODO division
    # def __truediv__(self, other):
    #     if not isinstance(other, CTypeWrapper):
    #         # TODO: smarter casts
    #         other_var = f'(double)({other})'
    #     else:
    #         other_var = self.context.cast(other, 'double').var
    #     double_self = self.context.cast(self, 'double')
    #     new_var = self.context.get_var(self.type)
    #     self.context.code_line(f'{new_var} = {double_self.var} / {other_var}')
    #     return CTypeWrapper(self.context, new_var, self.type)

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
        new_var = self.context.get_varname(self.type)
        self.context.code_line(f'{new_var} = -{self.var}')
        return CTypeWrapper(self.context, new_var, self.type)

    def __str__(self):
        return f'{self.type} {self.var}'


def codegen_compile(func, return_type, *arg_types):
    """
    :param func:
    :param datatype: either 'float', 'double' or 'int'
    :return:
    """
    func_name = func.__name__
    sig = signature(func)
    assert len(arg_types) + 1 == len(sig.parameters)

    return_typeinfo = normalize_to_type_info(return_type)
    if return_typeinfo is None:
        return None
    return_codegen_type = return_typeinfo.codegen_type

    context = Context()
    codegen_params = [context.get_var_wrapper(normalize_to_type_info(t)) for t in arg_types]
    header_params = [p.type + ' ' + p.var for p in codegen_params]

    # header
    context._code = f"""
#include <stdint.h>
{return_codegen_type} {func_name}({','.join(header_params)}){{
"""

    ret = func(context, *codegen_params)
    code = context._code
    code += f'return {ret.var};\n}}\n'

    fd, code_file_path = tempfile.mkstemp(prefix='codegen_', suffix='.c', text=True)
    os.close(fd)
    # code_file_path = '/tmp/testfile.c'

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
        cfunc.restype = return_typeinfo.ctype
        cfunc.argtypes = [normalize_to_type_info(t).ctype for t in arg_types]

    finally:
        # os.unlink(code_file_path)
        os.unlink(lib_file_path)

    setattr(cfunc, 'source', code)

    return cfunc
