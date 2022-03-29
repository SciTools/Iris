# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Test function :func:`iris.util._unmask_mask"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests  # isort:skip

import dask.array as da
import numpy as np
import numpy.ma as ma

import iris._lazy_data
from iris.util import _unmask_mask


class TestReal(tests.IrisTest):
    """Tests with numpy."""

    def setUp(self):
        self.al = np

    def check_result(self, result, expected):
        self.assertFalse(ma.is_masked(result))
        np.testing.assert_array_equal(result, expected)

    def test_plain_array(self):
        in_array = np.array([0, 1, 0, 1])
        result = _unmask_mask(self.al, in_array)
        self.check_result(result, in_array)

    def test_masked_array(self):
        in_array = ma.masked_array([0, 1, 0, 1], mask=[0, 0, 1, 1])
        result = _unmask_mask(self.al, in_array)
        self.check_result(result, [0, 1, 0, 0])


class TestLazy(TestReal):
    """Tests with dask."""

    def setUp(self):
        self.al = da

    def check_result(self, result, expected):
        self.assertTrue(iris._lazy_data.is_lazy_data(result))
        computed = result.compute()
        super().check_result(computed, expected)

    def test_lazy_array(self):
        in_array = da.from_array([0, 1, 0, 1])
        result = _unmask_mask(self.al, in_array)
        self.check_result(result, [0, 1, 0, 1])

    def test_lazy_masked_array(self):
        in_array = da.ma.masked_array([0, 1, 0, 1], mask=[1, 1, 0, 0])
        result = _unmask_mask(self.al, in_array)
        self.check_result(result, [0, 0, 0, 1])


if __name__ == "__main__":
    tests.main()
