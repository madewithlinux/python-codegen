class Match:
    def __init__(self):
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
        return self.result


