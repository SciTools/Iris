# (C) British Crown Copyright 2018, Met Office
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
"""Test function :func:`iris._lazy data.co_realise_cubes`."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from mock import MagicMock
import numpy as np

from iris.cube import Cube
from iris._lazy_data import as_lazy_data

from iris._lazy_data import co_realise_cubes


class ArrayAccessCounter(object):
    def __init__(self, array):
        self.dtype = array.dtype
        self.shape = array.shape
        self._array = array
        self.access_count = 0

    def __getitem__(self, keys):
        self.access_count += 1
        return self._array[keys]


class Test_co_realise_cubes(tests.IrisTest):
    def test_empty(self):
        self.assertEqual(co_realise_cubes([]), [])

    def test_basic(self):
        real_data = np.arange(3.)
        cube = Cube(as_lazy_data(real_data))
        self.assertTrue(cube.has_lazy_data())
        result, = co_realise_cubes([cube])
        self.assertEqual(result, cube)
        self.assertFalse(cube.has_lazy_data())
        self.assertArrayAllClose(cube.core_data(), real_data)

    def test_multi(self):
        real_data = np.arange(3.)
        cube = Cube(as_lazy_data(real_data))
        self.assertTrue(cube.has_lazy_data())
        cube_2 = cube + 1
        cube_3 = cube + 2
        cubes = [cube, cube_2, cube_3]
        for cube in cubes:
            self.assertTrue(cube.has_lazy_data())
        results = co_realise_cubes(cubes)
        self.assertEqual(results, cubes)
        for cube in cubes:
            self.assertFalse(cube.has_lazy_data())

    def test_combined_access(self):
        wrapped_array = ArrayAccessCounter(np.arange(3.))
        lazy_array = as_lazy_data(wrapped_array)
        derived_a = lazy_array + 1
        derived_b = lazy_array + 2
        cube_a = Cube(derived_a)
        cube_b = Cube(derived_b)
        co_realise_cubes([cube_a, cube_b])
        # Though used twice, the source data should only get fetched once.
        self.assertEqual(wrapped_array.access_count, 1)


if __name__ == '__main__':
    tests.main()
