class Context:
    @staticmethod
    def match(var):
        return _Match(var)

    @staticmethod
    def literal(x, type):
        return type(x)

    @staticmethod
    def cast(x, type):
        return Context.literal(x, type)

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


default_context = Context()


class _Match:
    def __init__(self, out):
        self.out = out
        self.result = None
        self.hasResult = False

    def case(self, condition: bool):
        # parameters, I guess?
        def foo(func):
            if not self.hasResult and condition:
                self.result = func()
                self.hasResult = True

        return foo

    def default(self):
        def foo(func):
            if not self.hasResult:
                self.result = func()
                self.hasResult = True

        return foo

    def get_result(self):
        assert self.hasResult
        if hasattr(self.out, 'from_atoms') and hasattr(self.result, 'to_atoms'):
            self.out.from_atoms(self.result.to_atoms())
        else:
            self.out = self.result
        return self.result


if __name__ == '__main__':
    # self test
    def foo(x: int) -> int:
        c = match(x)

        @c.case(x < 4)
        def d():
            return x * 8

        @c.case(4 <= x < 8)
        def d():
            return x * 3 - 4

        @c.case(x >= 8)
        def d():
            return x - 3

        return c.get_result()


    for x in range(10):
        expected = -1
        if x < 4:
            expected = x * 8
        elif 4 <= x < 8:
            expected = x * 3 - 4
        elif x >= 8:
            expected = x - 3
        actual = foo(x)
        if expected != actual:
            print(x, expected, actual)
            break
    else:
        print("success")
