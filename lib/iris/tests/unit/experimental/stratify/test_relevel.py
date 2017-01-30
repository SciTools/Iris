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
Unit tests for the
:func:`iris.experimental.stratify.relevel` function.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from functools import partial

import numpy as np
from numpy.testing import assert_array_equal
import stratify

import iris
from iris.experimental.stratify import relevel
import iris.tests.stock as stock


class Test(tests.IrisTest):
    def setUp(self):
        cube = stock.simple_3d()[:, :1, :1]

        #: The data from which to get the levels.
        self.level_data = cube.copy()
        #: The data to interpolate.
        self.phenom = cube.copy()

        self.phenom.rename('foobar')
        self.phenom *= 10

    def test_standard_input(self):
        result = relevel(self.phenom, self.level_data,
                          [-1, 0, 5.5],
                          self.level_data.coord('wibble'))
        assert_array_equal(result.data.flatten(),
                           np.array([np.nan, 0, 55]))
        expected = iris.coords.DimCoord([-1, 0, 5.5], standard_name=None,
                                        units=1, long_name='thingness')
        self.assertEqual(expected, result.coord('thingness'))

    def test_non_monotonic(self):
        result = relevel(self.phenom, self.level_data,
                          [2, 3, 2], self.level_data.coord('wibble'))
        assert_array_equal(result.data.flatten(),
                           np.array([20, 30, np.nan]))
        expected = iris.coords.AuxCoord([2, 3, 2], units=1,
                                        long_name='thingness')
        self.assertEqual(result.coord('thingness'), expected)

    def test_static_level(self):
        result = relevel(self.phenom, self.level_data,
                          [2, 2], self.level_data.coord('wibble'))
        assert_array_equal(result.data.flatten(),
                           np.array([20, 20]))

    def test_coord_input(self):
        source = iris.coords.AuxCoord(self.level_data.data)
        source.metadata = self.level_data.metadata
        result = relevel(self.phenom, source,
                          [0, 12, 13],
                          self.level_data.coord('wibble'))
        self.assertEqual(result.shape, (3, 1, 1))
        assert_array_equal(result.data.flatten(),
                           [0, 120, np.nan])
 
    def test_custom_interpolator(self):
        interpolator = partial(stratify.interpolate,
                               interpolation='nearest')
        result = relevel(self.phenom, self.level_data,
                          [-1, 0, 6.5],
                          self.level_data.coord('wibble'),
                         interpolator=interpolator)
        assert_array_equal(result.data.flatten(),
                           np.array([np.nan, 0, 120]))

    def test_multi_dim_target_levels(self):
        interpolator = partial(stratify.interpolate,
                               interpolation='linear',
                               extrapolation='linear')

        result = relevel(self.phenom, self.level_data,
                         self.level_data.data,
                         self.level_data.coord('wibble'),
                         interpolator=interpolator)
        assert_array_equal(result.data.flatten(),
                           np.array([0, 120]))
        self.assertCML(result) 


if __name__ == "__main__":
    tests.main()
