# (C) British Crown Copyright 2010 - 2015, Met Office
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
Tests elements of the cartography module.

"""

from __future__ import (absolute_import, division, print_function)

import six

# import iris tests first so that some things can be initialised before importing anything else
import iris.tests as tests

import numpy as np

import iris
import iris.analysis.cartography


class Test_get_xy_grids(tests.IrisTest):
    # Testing for iris.analysis.carography.get_xy_grids().

    def test_1d(self):
        cube = iris.cube.Cube(np.arange(12).reshape(3, 4))
        cube.add_dim_coord(iris.coords.DimCoord(np.arange(3), "latitude"), 0)
        cube.add_dim_coord(iris.coords.DimCoord(np.arange(4), "longitude"), 1)
        x, y = iris.analysis.cartography.get_xy_grids(cube)
        self.assertRepr((x, y), ("cartography", "get_xy_grids", "1d.txt"))

    def test_2d(self):
        cube = iris.cube.Cube(np.arange(12).reshape(3, 4))
        cube.add_aux_coord(iris.coords.AuxCoord(
                                np.arange(12).reshape(3, 4),
                                "latitude"), (0, 1))
        cube.add_aux_coord(iris.coords.AuxCoord(
                                np.arange(100, 112).reshape(3, 4),
                                "longitude"), (0, 1))
        x, y = iris.analysis.cartography.get_xy_grids(cube)
        self.assertRepr((x, y), ("cartography", "get_xy_grids", "2d.txt"))

    def test_3d(self):
        cube = iris.cube.Cube(np.arange(60).reshape(5, 3, 4))
        cube.add_aux_coord(iris.coords.AuxCoord(
                                np.arange(60).reshape(5, 3, 4),
                                "latitude"), (0, 1, 2))
        cube.add_aux_coord(iris.coords.AuxCoord(
                                np.arange(100, 160).reshape(5, 3, 4),
                                "longitude"), (0, 1, 2))
        self.assertRaises(ValueError, iris.analysis.cartography.get_xy_grids, cube)


if __name__ == "__main__":
    tests.main()
