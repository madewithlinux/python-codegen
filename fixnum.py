import numpy as np
import control


def default_type_factory(x, type):
    return type(x)


wordMask = np.uint64(0x00000000FFFFFFFF)


class FixNum:
    def __init__(self, num_words=4, type_factory=default_type_factory):
        self.num_words = num_words
        self.type_factory = type_factory
        self.sign = type_factory(0, np.int32)
        self.mantissa = [type_factory(0, np.uint32) for x in range(self.num_words)]

    @staticmethod
    def from_int(x, words=4):
        if hasattr(x, 'codegen_type_factory'):
            factory = x.codegen_type_factory
        else:
            factory = default_type_factory
        fx = FixNum(words, factory)
        fx.mantissa[0] = factory(x, np.uint32)
        m = control.match(fx.sign)
        m.case(x > 0)(lambda: factory(1, np.uint32))
        m.case(x < 0)(lambda: factory(-1, np.uint32))
        m.case(x == 0)(lambda: factory(0, np.uint32))
        fx.sign = m.get_result()
        return fx

    def clone_zero(self):
        return FixNum(num_words=self.num_words,
                      type_factory=self.type_factory)

    def to_atoms(self):
        return [self.sign] + self.mantissa

    def from_atoms(self, atoms: list):
        assert len(atoms) == 1 + self.num_words
        self.sign = atoms[0]
        self.mantissa = atoms[1:]

    def __add__(self, other: 'FixNum'):
        # TODO
        return None

    def __sub__(self, other: 'FixNum'):
        # TODO
        return None

    def __mul__(self, y: 'FixNum'):
        x = self
        z = x.clone_zero()
        m = control.match(x.sign)

        @m.case(control.logical_and(x.sign == 0, y.sign == 0))
        def foo():
            return z

        @m.default()
        def default():
            z.sign = x.sign * y.sign
            aux = [x.type_factory(0, np.uint32) for a in range(self.num_words)]
            for i in range(self.num_words):
                for j in range(self.num_words):
                    k = i + j
                    if k > x.num_words:
                        continue
                    u1 = x.mantissa[i] * y.mantissa[j]
                    u0 = u1 & wordMask
                    u1 = u1 >> np.uint64(32)
                    if k < self.num_words:
                        aux[k] = aux[k] + u0
                    if k > 0:
                        aux[k - 1] = aux[k - 1] + u1

            # propagate carry
            c = self.type_factory(0, np.uint64)
            for i in range(x.num_words - 1, -1, -1):
                c = aux[i] + c
                z.mantissa[i] = c & wordMask
                c = c >> np.uint64(32)
            return z

        return m.get_result()

    def __truediv__(self, other: 'FixNum'):
        # TODO
        return None

    def __str__(self):
        return f"{self.sign}, {self.mantissa}"
