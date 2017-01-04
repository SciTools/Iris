# (C) British Crown Copyright 2016, Met Office
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
"""Integration tests for experimental regridding."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import cartopy.crs as ccrs
from cf_units import Unit
import numpy as np

import iris
import iris.aux_factory
from iris.coord_systems import GeogCS
from iris.tests.stock import global_pp
from iris.experimental.regrid import (ProjectedUnstructuredLinear,
                                      ProjectedUnstructuredNearest)


@tests.skip_data
class TestProjectedUnstructured(tests.IrisTest):
    def setUp(self):
        path = tests.get_data_path(('NetCDF', 'unstructured_grid',
                                   'theta_nodal_xios.nc'))
        self.src = iris.load_cube(path, 'Potential Temperature')

        src_lat = self.src.coord('latitude')
        src_lon = self.src.coord('longitude')
        src_lat.coord_system = src_lon.coord_system = GeogCS(6370000)
        src_lat.convert_units(Unit('degrees'))
        src_lon.convert_units(Unit('degrees'))

        self.global_grid = global_pp()

    def test_nearest(self):
        res = self.src.regrid(self.global_grid, ProjectedUnstructuredNearest())
        self.assertArrayShapeStats(res, (1, 6, 73, 96),
                                   315.8913582, 11.00063766248)

    def test_nearest_sinusoidal(self):
        crs = ccrs.Sinusoidal()
        res = self.src.regrid(self.global_grid,
                              ProjectedUnstructuredNearest(crs))
        self.assertArrayShapeStats(res, (1, 6, 73, 96),
                                   315.891358296, 11.000639227, rtol=1e-8)

    def test_nearest_gnomonic_uk_domain(self):
        crs = ccrs.Gnomonic(central_latitude=60.0)
        uk_grid = self.global_grid.intersection(longitude=(-20, 20),
                                                latitude=(40, 80))
        res = self.src.regrid(uk_grid, ProjectedUnstructuredNearest(crs))

        self.assertArrayShapeStats(res, (1, 6, 17, 11),
                                   315.8873266, 11.0006664668, rtol=1e-8)
        expected_subset = np.array([[318.936829, 318.936829, 318.936829],
                                    [318.936829, 318.936829, 318.936829],
                                    [318.935163, 318.935163, 318.935163]])
        self.assertArrayAlmostEqual(expected_subset,
                                    res.data[0, 3, 5:8, 4:7].data)

    def test_nearest_aux_factories(self):
        src = self.src

        xy_dim_len, = src.coord(axis='X').shape
        z_dim_len, = src.coord('levels').shape

        src.add_aux_coord(iris.coords.AuxCoord(np.arange(z_dim_len)+40,
                                               long_name="level_height",
                                               units="m"), 1)
        src.add_aux_coord(iris.coords.AuxCoord(np.arange(z_dim_len)+50,
                                               long_name="sigma",
                                               units="1"), 1)
        src.add_aux_coord(iris.coords.AuxCoord(np.arange(xy_dim_len)+100,
                                               long_name="surface_altitude",
                                               units="m"), 2)
        src.add_aux_factory(iris.aux_factory.HybridHeightFactory(
            delta=src.coord("level_height"),
            sigma=src.coord("sigma"),
            orography=src.coord("surface_altitude")))
        res = src.regrid(self.global_grid, ProjectedUnstructuredNearest())

        self.assertArrayShapeStats(res, (1, 6, 73, 96),
                                   315.8913582, 11.00063766248)
        self.assertEqual(res.coord('altitude').shape, (6, 73, 96))

    def test_linear_sinusoidal(self):
        res = self.src.regrid(self.global_grid, ProjectedUnstructuredLinear())
        self.assertArrayShapeStats(res, (1, 6, 73, 96),
                                   315.8914839, 11.0006338412, rtol=1e-8)
        expected_subset = np.array([[299.999987, 299.999996, 299.999999],
                                    [299.999984, 299.999986, 299.999988],
                                    [299.999973, 299.999977, 299.999982]])
        self.assertArrayAlmostEqual(expected_subset,
                                    res.data[0, 0, 20:23, 40:43].data)

    def test_use_default_rtol(self):
        # TODO Remove before this change is merged in.
        linear_res = self.src.regrid(self.global_grid,
                                     ProjectedUnstructuredLinear())
        nearest_res = self.src.regrid(self.global_grid,
                                      ProjectedUnstructuredNearest())

        self.assertArrayShapeStats(linear_res, (1, 6, 73, 96),
                                   315.891483943, 11.0006338412)
        self.assertArrayShapeStats(nearest_res, (1, 6, 73, 96),
                                   315.891483943, 11.0006338412)


if __name__ == "__main__":
    tests.main()
