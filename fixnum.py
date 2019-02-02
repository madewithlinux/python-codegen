import numpy as np
import control


def DefaultUIntFactory(x):
    return np.uint64(x)


def DefaultIntFactory(x):
    return np.int64(x)


wordMask = 0x00000000FFFFFFFF


class FixNum:
    def __init__(self, words=4, intFactory=DefaultIntFactory, uintFactory=DefaultUIntFactory):
        self.words = words
        self.sign = intFactory(0)
        self.mantissa = [uintFactory(0) for x in range(self.words)]
        self.intFactory = intFactory
        self.uintFactory = uintFactory

    def clone_zero(self):
        return FixNum(words=self.words,
                      intFactory=self.intFactory,
                      uintFactory=self.uintFactory)

    def __add__(self, other: 'FixNum'):
        # TODO
        return None

    def __sub__(self, other: 'FixNum'):
        # TODO
        return None

    def __mul__(x, y: 'FixNum'):
        z = x.clone_zero()
        m = control.Match()

        @m.case(x.sign == 0 and y.sign == 0)
        def foo():
            return z

        @m.default()
        def default():
            z.sign = x.sign * y.sign
            for i in range(x.words):
                for j in range(x.words):
                    k = i + j
                    if k > x.words:
                        continue
                    u1 = x.mantissa[i] * y.mantissa[j]
                    u0 = u1 & wordMask
                    u1 = u1 >> 32
                    if k < x.words:
                        z.mantissa[k] = z.mantissa[k] + u0
                    if k > 0:
                        z.mantissa[k-1] = z.mantissa[k-1] + u1
            # TODO

        return m.get_result()

    def __truediv__(self, other: 'FixNum'):
        # TODO
        return None
