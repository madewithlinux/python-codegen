from inspect import signature

# this is basically the whole LLVM layer
I = 0
STACK = []


class LLVMCode:
    def __init__(self, io, code=''):  # the only constructor for now is by double* instruction
        self.io = io
        self.code = code

    def __getitem__(self, i):
        global I, STACK
        copy_code = "%" + str(I + 1) + " = getelementptr inbounds double, double* " + self.io + ", i64 " + str(i) + "\n"
        copy_code += "%" + str(I + 2) + " = load double, double* %" + str(I + 1) + ", align 8\n"
        I += 2
        STACK += [I]
        return LLVMCode(self.io, copy_code)

    def __setitem__(self, i, other_llvcode):
        global I, STACK
        self.code += other_llvcode.code
        self.code += "%" + str(I + 1) + " = getelementptr inbounds double, double* " + self.io + ", i64 " + str(
            i) + "\n"
        self.code += "store double %" + str(I) + ", double* %" + str(I + 1) + ", align 8\n"
        I += 1
        STACK = STACK[:-1]
        return self

    def general_arithmetics(self, operator, other_llvcode):
        global I, STACK
        self.code += other_llvcode.code
        self.code += "%" + str(I + 1) + " = f" + operator + " double %" + str(STACK[-2]) + ", %" + str(
            STACK[-1]) + "\n"
        I += 1
        STACK = STACK[:-2] + [I]
        return self

    def __add__(self, other_llvcode):
        return self.general_arithmetics('add', other_llvcode)

    def __sub__(self, other_llvcode):
        return self.general_arithmetics('sub', other_llvcode)

    def __mul__(self, other_llvcode):
        return self.general_arithmetics('mul', other_llvcode)

    def __truediv__(self, other_llvcode):
        return self.general_arithmetics('div', other_llvcode)


param_names = [chr(i) for i in range(ord('a'), ord('z') + 1)]

head = """; ModuleID = ''
target triple = "unknown-unknown-unknown"
target datalayout = ""

; Function Attrs: nounwind uwtable
define void @{name}({params}) #0 {{ 
"""

tail = """ret {return_name}
}}
"""

def codegen(func):
    global I, STACK
    func_name = func.__name__
    sig = signature(func)
    params = [LLVMCode('%'+c) for c in param_names[:len(sig.parameters)]]
    # params = [LLVMCode('%a'), LLVMCode('%b')]
    param_declaration = ', '.join(
        'double* ' + c.io for c in params
    )
    code = func(*params)
    return ''.join([
        head.format(name=func_name, params=param_declaration),
        code.code,
        tail.format(return_name='%'+str(I))
    ])
