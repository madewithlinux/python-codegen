import abc


class Context(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def match(vaself, r): pass

    @abc.abstractmethod
    def literal(self, x, type): pass

    @abc.abstractmethod
    def cast(self, x, type): pass

    @abc.abstractmethod
    def logical_and(self, a, b): pass

    @abc.abstractmethod
    def logical_or(self, a, b): pass


class DefaultContext(Context):
    def match(self, var):
        return _Match(var)

    def literal(self, x, type):
        return type(x)

    def cast(self, x, type):
        return self.literal(x, type)

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


default_context = DefaultContext()


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
