# (C) British Crown Copyright 2014 - 2015, Met Office
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
Test function
:func:`iris.experimental.regrid.regrid_area_weighted_rectilinear_src_and_grid`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

import numpy as np
import numpy.ma as ma

from iris.coords import DimCoord
from iris.coord_systems import GeogCS
from iris.cube import Cube
from iris.experimental.regrid \
    import regrid_area_weighted_rectilinear_src_and_grid as regrid
from iris.tests.experimental.regrid.\
    test_regrid_area_weighted_rectilinear_src_and_grid import \
    _resampled_grid


class Common(tests.IrisTest):
    def setUp(self):
        # A (3, 2, 4) cube.
        cube = Cube(np.ma.arange(24, dtype=np.int32).reshape((3, 2, 4)))
        cs = GeogCS(6371229)
        coord = DimCoord(points=np.array([-1, 0, 1], dtype=np.int32),
                         standard_name='latitude',
                         units='degrees',
                         coord_system=cs)
        cube.add_dim_coord(coord, 0)
        coord = DimCoord(points=np.array([-1, 0, 1, 2], dtype=np.int32),
                         standard_name='longitude',
                         units='degrees',
                         coord_system=cs)
        cube.add_dim_coord(coord, 2)
        cube.coord('latitude').guess_bounds()
        cube.coord('longitude').guess_bounds()
        self.src_cube = cube
        # Create (7, 2, 9) grid cube.
        self.grid_cube = _resampled_grid(cube, 2.3, 2.4)


class TestMdtol(Common, tests.IrisTest):
    # Tests to check the masking behaviour controlled by mdtol kwarg.
    def setUp(self):
        super(TestMdtol, self).setUp()
        self.src_cube.data[1, 1, 2] = ma.masked

    def test_default(self):
        res = regrid(self.src_cube, self.grid_cube)
        expected_mask = np.zeros((7, 2, 9), bool)
        expected_mask[2:5, 1, 4:7] = True
        self.assertArrayEqual(res.data.mask, expected_mask)

    def test_zero(self):
        res = regrid(self.src_cube, self.grid_cube, mdtol=0)
        expected_mask = np.zeros((7, 2, 9), bool)
        expected_mask[2:5, 1, 4:7] = True
        self.assertArrayEqual(res.data.mask, expected_mask)

    def test_one(self):
        res = regrid(self.src_cube, self.grid_cube, mdtol=1)
        expected_mask = np.zeros((7, 2, 9), bool)
        # Only a single cell has all contributing cells masked.
        expected_mask[3, 1, 5] = True
        self.assertArrayEqual(res.data.mask, expected_mask)

    def test_fraction_below_min(self):
        # Cells in target grid that overlap with the masked src cell
        # have the following fractions (approx. due to spherical area).
        #   4      5      6      7
        # 2 ----------------------
        #   | 0.33 | 0.66 | 0.50 |
        # 3 ----------------------
        #   | 0.33 | 1.00 | 0.75 |
        # 4 ----------------------
        #   | 0.33 | 0.66 | 0.50 |
        # 5 ----------------------
        #

        # Threshold less than minimum fraction.
        mdtol = 0.2
        res = regrid(self.src_cube, self.grid_cube, mdtol=mdtol)
        expected_mask = np.zeros((7, 2, 9), bool)
        expected_mask[2:5, 1, 4:7] = True
        self.assertArrayEqual(res.data.mask, expected_mask)

    def test_fraction_between_min_and_max(self):
        # Threshold between min and max fraction. See
        # test_fraction_below_min() comment for picture showing
        # the fractions of masked data.
        mdtol = 0.6
        res = regrid(self.src_cube, self.grid_cube, mdtol=mdtol)
        expected_mask = np.zeros((7, 2, 9), bool)
        expected_mask[2:5, 1, 5] = True
        expected_mask[3, 1, 6] = True
        self.assertArrayEqual(res.data.mask, expected_mask)

    def test_src_not_masked_array(self):
        self.src_cube.data = self.src_cube.data.filled(1.0)
        res = regrid(self.src_cube, self.grid_cube, mdtol=0.9)
        self.assertFalse(ma.isMaskedArray(res.data))

    def test_boolean_mask(self):
        self.src_cube.data = np.ma.arange(24).reshape(3, 2, 4)
        res = regrid(self.src_cube, self.grid_cube, mdtol=0.9)
        self.assertEqual(ma.count_masked(res.data), 0)

    def test_scalar_no_overlap(self):
        # Slice src so result collapses to a scalar.
        src_cube = self.src_cube[:, 1, :]
        # Regrid to a single cell with no overlap with masked src cells.
        grid_cube = self.grid_cube[2, 1, 3]
        res = regrid(src_cube, grid_cube, mdtol=0.8)
        self.assertFalse(ma.isMaskedArray(res.data))

    def test_scalar_with_overlap_below_mdtol(self):
        # Slice src so result collapses to a scalar.
        src_cube = self.src_cube[:, 1, :]
        # Regrid to a single cell with 50% overlap with masked src cells.
        grid_cube = self.grid_cube[3, 1, 4]
        # Set threshold (mdtol) to greater than 0.5 (50%).
        res = regrid(src_cube, grid_cube, mdtol=0.6)
        self.assertEqual(ma.count_masked(res.data), 0)

    def test_scalar_with_overlap_above_mdtol(self):
        # Slice src so result collapses to a scalar.
        src_cube = self.src_cube[:, 1, :]
        # Regrid to a single cell with 50% overlap with masked src cells.
        grid_cube = self.grid_cube[3, 1, 4]
        # Set threshold (mdtol) to less than 0.5 (50%).
        res = regrid(src_cube, grid_cube, mdtol=0.4)
        self.assertEqual(ma.count_masked(res.data), 1)


class TestExceptions(Common, tests.IrisTest):
    def test_no_bounds(self):
        self.src_cube.coord('latitude').bounds = None
        msg = ('The horizontal grid coordinates of both the source and grid '
               'cubes must have contiguous bounds.')
        with self.assertRaisesRegexp(ValueError, msg):
            regrid(self.src_cube, self.grid_cube)

    def test_non_contiguous_bounds(self):
        coord = self.src_cube.coord('latitude')
        bounds = coord.bounds.copy()
        bounds[1, 1] -= 0.1
        coord.bounds = bounds
        msg = ('The horizontal grid coordinates of both the source and grid '
               'cubes must have contiguous bounds.')
        with self.assertRaisesRegexp(ValueError, msg):
            regrid(self.src_cube, self.grid_cube)

    def test_missing_coords(self):
        self.src_cube.remove_coord('latitude')
        msg = "Cube 'unknown' must contain a single 1D y coordinate."
        with self.assertRaisesRegexp(ValueError, msg):
            regrid(self.src_cube, self.grid_cube)

    def test_diff_cs(self):
        y_coord = self.src_cube.coord('latitude')
        y_coord.coord_system.semi_major_axis = 7000000
        msg = ('The horizontal grid coordinates of both the source and grid '
               'cubes must have the same coordinate system.')
        with self.assertRaisesRegexp(ValueError, msg):
            regrid(self.src_cube, self.grid_cube)


class TestValue(Common, tests.IrisTest):
    def test_regrid_same_grid(self):
        res_cube = regrid(self.src_cube, self.src_cube)
        self.assertEqual(res_cube, self.src_cube)
        self.assertArrayAlmostEqual(res_cube.data, self.src_cube.data)


if __name__ == '__main__':
    tests.main()
