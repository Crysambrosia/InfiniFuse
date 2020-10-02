import math
import pytest
import struct
from .nbt2 import *


class TagTester():
    """Parent class of other tests"""
    
    def operator(self,
        normal, 
        reverse,
        result, 
        reverseResult = None,
        cls = None,
        reverseCls = None
    ):
        """Test a particular operator in both directions
        normal           : operation w/ tag as first argument
        reverse          : operation w/ tag as last argument
        result           : expected result of normal
        reverseResult    : expected result of reverse, defaults to result
        cls              : expected class of normal, defaults to self.tag.__class__
        reverseCls       : expected class of reverse, defaults to None (not checked)
        """
        
        if reverseResult is None:
            reverseResult = result
        
        if cls is None:
            cls = self.tag.__class__

        assert isinstance(normal, cls)
        assert normal == result
        
        if reverseCls is not None:
            assert isinstance(reverse, reverseCls)
        assert reverse == reverseResult
    
class TestTAG_Byte(TagTester):

    def setup_method(self, method):
        self.tag = TAG_Byte(16)

    def test_eq(self):
        self.operator(
            normal = self.tag == 16,
            reverse = 16 == self.tag,
            result = True,
            cls = bool,
            reverseCls = bool
        )
        self.operator(
            normal = self.tag == 17,
            reverse = 17 == self.tag,
            result = False,
            cls = bool,
            reverseCls = bool
        )

    def test_ne(self):
        self.operator(
            normal = self.tag != 17,
            reverse = 17 != self.tag,
            result = True,
            cls = bool,
            reverseCls = bool
        )
        self.operator(
            normal = self.tag != 16,
            reverse = 16 != self.tag,
            result = False,
            cls = bool,
            reverseCls = bool
        )

    def test_lt(self):
        self.operator(
            normal = self.tag < 17,
            reverse = 15 < self.tag,
            result = True,
            cls = bool,
            reverseCls = bool
        )
        self.operator(
            normal = self.tag < 12,
            reverse = 16 < self.tag,
            result = False,
            cls = bool,
            reverseCls = bool
        )

    def test_le(self):
        self.operator(
            normal = self.tag <= 16,
            reverse = 15 <= self.tag,
            result = True,
            cls = bool,
            reverseCls = bool
        )
        self.operator(
            normal = self.tag <= 12,
            reverse = 24 <= self.tag,
            result = False,
            cls = bool,
            reverseCls = bool
        )

    def test_gt(self):
        self.operator(
            normal = self.tag > 15,
            reverse = 17 > self.tag,
            result = True,
            cls = bool,
            reverseCls = bool
        )
        self.operator(
            normal = self.tag > 17,
            reverse = 16 > self.tag,
            result = False,
            cls = bool,
            reverseCls = bool
        )

    def test_ge(self):
        self.operator(
            normal = self.tag >= 16,
            reverse = 17 >= self.tag,
            result = True,
            cls = bool,
            reverseCls = bool
        )
        self.operator(
            normal = self.tag >= 24,
            reverse = 12 >= self.tag,
            result = False,
            cls = bool,
            reverseCls = bool
        )

    def test_int(self):
        assert int(self.tag) == 16

    def test_float(self):
        assert float(self.tag) == 16.0

    def test_add(self):
        self.operator(
            normal = self.tag + 8,
            reverse = 8 + self.tag,
            result = 24
        )

    def test_sub(self):
        self.operator(
            normal = self.tag -16,
            reverse = 16 - self.tag,
            result = 0
        )

    def  test_mul(self):
        self.operator(
            normal = self.tag * 2,
            reverse = 2*  self.tag,
            result = 32
        )

    def test_matmul(self):
        with pytest.raises(TypeError):
            self.tag @ 16
        with pytest.raises(TypeError):
            16 @ self.tag
 
    def test_truediv_int(self):
        self.operator(
            normal = self.tag / 2,
            reverse = 128 / self.tag,
            result = 8
        )

    def test_truediv_float(self):
        # With non-integer truediv, rounding should occur only in one direction
        self.operator(
            normal = self.tag / 3,
            reverse = 87 / self.tag,
            result = 5,
            reverseResult = 5.4375
        )

    def test_floordiv(self):
        self.operator(
            normal = self.tag // 6,
            reverse = 35 // self.tag,
            result = 2
        )

    def test_mod(self):
        self.operator(
            normal = self.tag % 6,
            reverse = 36 % self.tag,
            result = 4
        )

    def test_divmod(self):
        normal = divmod(self.tag, 6)
        reverse = divmod(36, self.tag)
        assert isinstance(normal, tuple)
        assert isinstance(reverse, tuple)
        assert normal == reverse == (2, 4)

    def test_pow(self):
        self.operator(
            normal = self.tag ** 1.5,
            reverse = 2 ** self.tag,
            result = 64, 
            reverseResult = 65536
        )
        
    def test_lshift(self):
        self.operator(
            normal = self.tag << 1,
            reverse = 1 << self.tag,
            result = 32,
            reverseResult = 65536
        )

    def test_rshift(self):
        self.operator(
            normal = self.tag >> 1,
            reverse = 524812 >> self.tag,
            result = 8
        )

    def test_and(self):
        self.operator(
            normal = self.tag & 82,
            reverse = 82 & self.tag,
            result = 16
        )

    def test_xor(self):
        self.operator(
            normal = self.tag ^ 82,
            reverse = 82 ^ self.tag,
            result = 66
        )

    def test_or(self):
        self.operator(
            normal = self.tag | 82,
            reverse = 82 | self.tag,
            result = 82
        )

    def test_neg(self):
        with pytest.raises(struct.error):
            -self.tag

    def test_pos(self):
        assert +self.tag == 16

    def test_abs(self):
        assert abs(self.tag) == 16
 
    def test_invert(self):
        with pytest.raises(struct.error):
            ~self.tag

    def test_round(self):
        assert round(self.tag) == 16

    def test_trunc(self):
        assert math.trunc(self.tag) == 16

    def test_floor(self):
        assert math.floor(self.tag) == 16

    def test_ceil(self):
        assert math.floor(self.tag) == 16