# (C) British Crown Copyright 2017, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""
Unit tests for the function :func:`iris.analysis.maths._get_dtype`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np
from numpy import ma

from iris.analysis.maths import _get_dtype
from iris.cube import Cube
from iris.coords import DimCoord, AuxCoord


class Test(tests.IrisTest):
    def _check_call(self, obj, expected_dtype):
        result = _get_dtype(obj)
        self.assertEqual(expected_dtype, result)

    def test_int8(self):
        n = -128
        self._check_call(n, np.int8)

    def test_int16(self):
        n = -129
        self._check_call(n, np.int16)

    def test_uint8(self):
        n = 255
        self._check_call(n, np.uint8)

    def test_uint16(self):
        n = 256
        self._check_call(n, np.uint16)

    def test_float16(self):
        n = 60000.0
        self._check_call(n, np.float16)

    def test_float32(self):
        n = 65000.0
        self._check_call(n, np.float32)

    def test_scalar_demote(self):
        n = np.int64(10)
        self._check_call(n, np.uint8)

    def test_array(self):
        a = np.array([1, 2, 3], dtype=np.int16)
        self._check_call(a, np.int16)

    def test_scalar_array(self):
        a = np.array(1, dtype=np.int32)
        self._check_call(a, np.int32)

    def test_masked_array(self):
        m = ma.masked_array([1, 2, 3], [1, 0, 1], dtype=np.float16)
        self._check_call(m, np.float16)

    def test_masked_constant(self):
        m = ma.masked
        self._check_call(m, m.dtype)

    def test_cube(self):
        data = np.array([1, 2, 3], dtype=np.float32)
        cube = Cube(data)
        self._check_call(cube, np.float32)

    def test_aux_coord(self):
        points = np.array([1, 2, 3], dtype=np.int64)
        aux_coord = AuxCoord(points)
        self._check_call(aux_coord, np.int64)

    def test_dim_coord(self):
        points = np.array([1, 2, 3], dtype=np.float16)
        dim_coord = DimCoord(points)
        self._check_call(dim_coord, np.float16)
