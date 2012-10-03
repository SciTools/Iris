# (C) British Crown Copyright 2010 - 2012, Met Office
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
Tests map creation.

"""

# import iris tests first so that some things can be initialised before importing anything else
import iris.tests as tests

import matplotlib.pyplot as plt
import numpy
import cartopy.crs as ccrs

import iris
import iris.coord_systems
import iris.cube
import iris.plot as iplt
import iris.tests.stock


class TestBasic(tests.IrisTest):
    cube = iris.tests.stock.realistic_4d()

    def test_contourf(self):
        cube = self.cube[0, 0]
        iplt.contourf(cube)
        self.check_graphic()

    def test_pcolor(self):
        cube = self.cube[0, 0]
        iplt.pcolor(cube)
        self.check_graphic()

    def test_unmappable(self):
        cube = self.cube[0, 0]
        cube.coord('grid_longitude').standard_name = None
        iplt.contourf(cube)
        self.check_graphic()


@iris.tests.skip_data
class TestUnmappable(tests.IrisTest):
    def setUp(self):
        src_cube = iris.tests.stock.global_pp()

        # Make a cube that can't be located on the globe.
        cube = iris.cube.Cube(src_cube.data)
        cube.add_dim_coord(iris.coords.DimCoord(numpy.arange(96, dtype=numpy.float32) * 100, long_name='x', units='m'), 1)
        cube.add_dim_coord(iris.coords.DimCoord(numpy.arange(73, dtype=numpy.float32) * 100, long_name='y', units='m'), 0)
        cube.standard_name = 'air_temperature'
        cube.units = 'K'
        cube.assert_valid()
        self.cube = cube

    def test_simple(self):
        iplt.contourf(self.cube)
        self.check_graphic()


# TODO: Remove
def _pretend_unrotated(cube):
    lat = cube.coord('grid_latitude')
    lon = cube.coord('grid_longitude')
    rcs = lat.coord_system

    lat.coord_system = rcs.ellipsoid
    lon.coord_system = rcs.ellipsoid
    lat.standard_name = "latitude"
    lon.standard_name = "longitude"
    
    lon.points = lon.points - 360
    if lon.bounds is not None:
        lon.bounds = lon.bounds - 360


@iris.tests.skip_data
class TestMappingSubRegion(tests.IrisTest):
    def setUp(self):
        cube_path = tests.get_data_path(('PP', 'aPProt1', 'rotatedMHtimecube.pp'))
        cube = iris.load_cube(cube_path)[0]
        # make the data slighly smaller to speed things up...
        self.cube = cube[::10, ::10]

    def test_simple(self):
        # First sub-plot
        plt.subplot(221)
        plt.title('Default')
        iplt.contourf(self.cube)
        plt.gca().coastlines()

        # Second sub-plot
        plt.subplot(222)
        plt.title('Molleweide')
        iplt.map_setup(projection=ccrs.Mollweide(central_longitude=120))
        iplt.contourf(self.cube)
        plt.gca().coastlines()

        # Third sub-plot
        plt.subplot(223)
        plt.title('Native')
        ax = iplt.map_setup(cube=self.cube)
        iplt.contour(self.cube)
        ax.coastlines()
        
        # Fourth sub-plot
        plt.subplot(224)
        plt.title('PlateCarree')
        ax = plt.subplot(2, 2, 4, projection=ccrs.PlateCarree())
        iplt.contourf(self.cube)
        ax.coastlines()

        self.check_graphic()


@iris.tests.skip_data
class TestLowLevel(tests.IrisTest):
    def setUp(self):
        self.cube = iris.tests.stock.global_pp()
        self.few = 4
        self.few_levels = range(280, 300, 5)
        self.many_levels = numpy.linspace(self.cube.data.min(), self.cube.data.max(), 40)

    def test_simple(self):
        iplt.contour(self.cube)
        self.check_graphic()

    def test_params(self):
        iplt.contourf(self.cube, self.few)
        self.check_graphic()

        iplt.contourf(self.cube, self.few_levels)
        self.check_graphic()

        iplt.contourf(self.cube, self.many_levels)
        self.check_graphic()

    def test_keywords(self):
        iplt.contourf(self.cube, levels=self.few_levels)
        self.check_graphic()

        iplt.contourf(self.cube, levels=self.many_levels, alpha=0.5)
        self.check_graphic()


@iris.tests.skip_data
class TestBoundedCube(tests.IrisTest):
    def setUp(self):
        self.cube = iris.tests.stock.global_pp()
        # Add some bounds to this data (this will actually make the bounds invalid as they 
        # will straddle the north pole and overlap on the date line, but that doesn't matter for this test.)
        self.cube.coord('latitude').guess_bounds()
        self.cube.coord('longitude').guess_bounds()

    def test_pcolormesh(self):
        # pcolormesh can only be drawn in native coordinates (or more specifically, in coordinates that don't wrap).
        plt.axes(projection=ccrs.PlateCarree(central_longitude=180))
        iplt.pcolormesh(self.cube)
        self.check_graphic()
        
    def test_grid(self):
        iplt.outline(self.cube)
        self.check_graphic()


@iris.tests.skip_data
class TestLimitedAreaCube(tests.IrisTest):
    def setUp(self):
        cube_path = tests.get_data_path(('PP', 'aPProt1', 'rotated.pp'))
        self.cube = iris.load_cube(cube_path)[::20, ::20]
        self.cube.coord('grid_latitude').guess_bounds()
        self.cube.coord('grid_longitude').guess_bounds()

    def test_pcolormesh(self):
        iplt.pcolormesh(self.cube)
        self.check_graphic()
        
    def test_grid(self):
        iplt.pcolormesh(self.cube, facecolors='none', edgecolors='blue')
        # the result is a graphic which has coloured edges. This is a mpl bug, see
        # https://github.com/matplotlib/matplotlib/issues/1302
        self.check_graphic()
    
    def test_outline(self):
        iplt.outline(self.cube)
        self.check_graphic()
    
    def test_scatter(self):    
        scatter = iplt.points(self.cube)
        plt.gca().coastlines()
        self.check_graphic()


if __name__ == "__main__":
    tests.main()
