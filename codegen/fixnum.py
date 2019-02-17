from __future__ import annotations

import numpy as np
from codegen import control
import functools

wordMask = np.uint64(0x00000000FFFFFFFF)


def clone_first(method):
    @functools.wraps(method)
    def new_method(self, *args, **kwds):
        return method(self.clone(), *args, **kwds)

    return new_method


class FixNum:
    def __init__(self, context: control.Context, num_words=4, sign=None, mantissa=None):
        self.context = context
        self.num_words = num_words
        if sign is None:
            self.sign = context.literal(0, np.int32)
        else:
            self.sign = sign
        if mantissa is None:
            self.mantissa = [context.literal(0, np.uint32) for x in range(self.num_words)]
        else:
            self.mantissa = mantissa

    @staticmethod
    def from_int(context: control.Context, x, num_words=4):
        x = context.literal(x, np.int32)
        m = context.match(context.literal(0, np.int32))
        m.case(x > 0)(lambda: context.literal(1, np.uint32))
        m.case(x < 0)(lambda: context.literal(-1, np.uint32))
        m.case(x == 0)(lambda: context.literal(0, np.uint32))
        sign = m.get_result()
        fx = FixNum(context=context, num_words=num_words, sign=sign)
        fx.mantissa[0] = context.literal(x, np.uint32)
        return fx

    @staticmethod
    def from_float_literal(context: control.Context, x: float, num_words=4):
        x0 = context.literal(np.uint32(x), np.uint32)
        x1 = context.literal(np.uint32((x * 2 ** 32) % 2 ** 32), np.uint32)
        x2 = context.literal(np.uint32((x * 2 ** 64) % 2 ** 64), np.uint32)

        sign = 0
        if x > 0:
            sign = 1
        elif x < 0:
            sign = -1
        fx = FixNum(context=context, num_words=num_words, sign=sign)
        fx.mantissa[0] = x0
        fx.mantissa[1] = x1
        fx.mantissa[2] = x2

        return fx

    def clone_zero(self) -> FixNum:
        return FixNum(context=self.context,
                      num_words=self.num_words)

    def clone(self) -> FixNum:
        z = FixNum(context=self.context,
                   num_words=self.num_words,
                   sign=self.sign,
                   mantissa=list(self.mantissa))
        return z

    def to_atoms(self):
        return [self.sign] + self.mantissa

    @clone_first
    def from_atoms(self, atoms: list) -> FixNum:
        assert len(atoms) == 1 + self.num_words
        self.sign = atoms[0]
        self.mantissa = atoms[1:]
        return self

    def assert_compatible(self, other):
        assert self.num_words == other.num_words

    def _words_reverse(self):
        return range(self.num_words - 1, -1, -1)

    def _words(self):
        return range(0, self.num_words)

    @clone_first
    def _check_zero(self) -> FixNum:
        """Make sure that sign==0 only if the entire mantissa is also zero"""
        z = self

        mantissa_or = z.mantissa[0]
        for i in range(1, z.num_words):
            mantissa_or = mantissa_or | z.mantissa[i]

        m = self.context.match(z.sign)
        m.case(z.sign == 0)(lambda: self.context.literal(0, np.int32))
        m.case(mantissa_or == 0)(lambda: self.context.literal(0, np.int32))
        m.default()(lambda: z.sign)
        z.sign = m.get_result()
        return z

    @clone_first
    def _add_words(self, g) -> FixNum:
        c = self.context.literal(0, np.uint64)
        z = self
        for i in z._words_reverse():
            c = c + \
                self.context.cast(z.mantissa[i], np.uint64) + \
                self.context.cast(g.mantissa[i], np.uint64)
            z.mantissa[i] = self.context.cast(c & wordMask, np.uint32)
            c = c >> np.uint64(32)
        return z

    @clone_first
    def _sub_words(self, other: FixNum) -> FixNum:
        c = self.context.literal(0, np.uint64)
        z = self
        x = other
        for i in z._words_reverse():
            y = self.context.cast(z.mantissa[i], np.uint64) - \
                self.context.cast(x.mantissa[i], np.uint64) - c
            z.mantissa[i] = self.context.cast(y & wordMask, np.uint32)
            m = self.context.match(c)
            m.case(y > self.context.literal(0x100000000, np.uint64))(lambda: self.context.literal(1, np.uint64))
            m.default()(lambda: self.context.literal(0, np.uint64))
            c = m.get_result()
        return z

    @clone_first
    def _cmp_words(self, other: FixNum) -> int:
        z = self
        x = other
        res = self.context.literal(0, int)
        m = self.context.match(res)
        for i in self._words():
            m.case(z.mantissa[i] > x.mantissa[i])(lambda: self.context.literal(1, int))
            m.case(z.mantissa[i] < x.mantissa[i])(lambda: self.context.literal(-1, int))
        m.default()(lambda: self.context.literal(0, int))
        return m.get_result()

    @clone_first
    def __add__(self, y: FixNum):
        self.assert_compatible(y)
        z = self
        m = self.context.match(z)
        m.case(y.sign == 0)(lambda: z)
        m.case(z.sign == 0)(lambda: y)
        m.case(z.sign == y.sign)(lambda: z._add_words(y))
        m.case(z._cmp_words(y) >= 0)(lambda: z._sub_words(y))
        # opposite signs, must subtract
        m.default()(lambda: y._sub_words(z))

        res: FixNum = m.get_result()
        res = res._check_zero()
        return res

    @clone_first
    def __sub__(self, other: FixNum) -> FixNum:
        # TODO
        assert False

    @clone_first
    def __mul__(self, y: FixNum):
        self.assert_compatible(y)
        x = self
        z = x.clone_zero()

        m = self.context.match(z)

        @m.case(self.context.logical_and(x.sign == 0, y.sign == 0))
        def foo():
            return z

        @m.default()
        def default():
            z.sign = x.sign * y.sign
            aux = [x.context.literal(0, np.uint32) for a in range(self.num_words)]
            for i in range(self.num_words):
                for j in range(self.num_words):
                    k = i + j
                    if k > x.num_words:
                        continue
                    u1 = self.context.cast(x.mantissa[i], np.uint64) * \
                         self.context.cast(y.mantissa[j], np.uint64)
                    u0 = u1 & wordMask
                    u1 = u1 >> np.uint64(32)
                    if k < self.num_words:
                        aux[k] = aux[k] + u0
                    if k > 0:
                        aux[k - 1] = aux[k - 1] + u1

            # propagate carry
            c = self.context.literal(0, np.uint64)
            for i in x._words_reverse():
                c = self.context.cast(aux[i], np.uint64) + c
                z.mantissa[i] = self.context.cast(c & wordMask, np.uint32)
                c = c >> np.uint64(32)
            return z

        return m.get_result()

    @clone_first
    def __truediv__(self, other: FixNum) -> FixNum:
        # TODO
        assert False
        return None

    def __str__(self):
        return f"{self.sign}, [{','.join(str(x) for x in self.mantissa)}]"

    @clone_first
    def to_float_imprecise(self):
        return self.context.cast(self.mantissa[0], np.float64) + \
               self.context.cast(self.mantissa[1], np.float64) * self.context.literal(1/(1 << 32), np.float64) + \
               self.context.cast(self.mantissa[2], np.float64) * self.context.literal(1/(1 << 64), np.float64)
