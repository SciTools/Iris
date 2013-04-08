# (C) British Crown Copyright 2013 Met Office
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
Test the :func:`iris.experimental.regrid._get_xy_dim_coords` function.

"""
# import iris tests first so that some things can be initialised
# before importing anything else.
import iris.tests as tests

import os

import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt

import ESMF

import cartopy.crs as ccrs
import iris
import iris.plot as iplt
import iris.quickplot as qplt
import iris.tests.stock as istk

from iris.experimental.regrid_conservative import regrid_conservative_via_esmpy


def _make_test_cube(shape, xlims, ylims, pole_latlon=None):
    """Create latlon cube (optionally rotated) with given xy dims+lims."""
    nx, ny = shape
    cube = iris.cube.Cube(np.zeros((ny, nx)))
    xvals = np.linspace(xlims[0], xlims[1], nx)
    yvals = np.linspace(ylims[0], ylims[1], ny)
    if pole_latlon is not None:
        coordname_prefix = 'grid_'
        pole_lat, pole_lon = pole_latlon
        cs = iris.coord_systems.RotatedGeogCS(
            grid_north_pole_latitude=pole_lat,
            grid_north_pole_longitude=pole_lon)
    else:
        coordname_prefix = ''
        cs = iris.coord_systems.GeogCS(6371229)

    co_x = iris.coords.DimCoord(xvals,
                                standard_name=coordname_prefix + 'longitude',
                                units=iris.unit.Unit('degrees'),
                                coord_system=cs)
    co_x.guess_bounds()
    cube.add_dim_coord(co_x, 1)
    co_y = iris.coords.DimCoord(yvals,
                                standard_name=coordname_prefix + 'latitude',
                                units=iris.unit.Unit('degrees'),
                                coord_system=cs)
    co_y.guess_bounds()
    cube.add_dim_coord(co_y, 0)
    return cube


def _generate_test_cubes():
    # create source test cube on rotated form
    pole_lat = 53.4
    pole_lon = -173.2
    deg_swing = 35.3
    pole_lon += deg_swing
    c1_nx = 7
    c1_ny = 5
    c1_xlims = -60.0, 60.0
    c1_ylims = -30.0, 30.0
    do_wrapped = False
    do_wrapped = True
    if do_wrapped:
        c1_xlims = [x + 360.0 for x in c1_xlims]
    c1_xlims = [x - deg_swing for x in c1_xlims]
    c1 = _make_test_cube((c1_nx, c1_ny), c1_xlims, c1_ylims,
                         pole_latlon=(pole_lat, pole_lon))
    c1.data = np.array([
        [100, 100, 100, 100, 100, 100, 100],
        [100, 199, 199, 199, 199, 100, 100],
        [100, 100, 100, 199, 199, 100, 100],
        [100, 100, 100, 199, 199, 199, 100],
        [100, 100, 100, 100, 100, 100, 100]],
        dtype=np.float)

    # construct target cube to receive
    nx2 = 10
    ny2 = 8
    c2_xlims = -150.0, 200.0
    c2_ylims = -60.0, 70.0
    c2 = _make_test_cube((nx2, ny2), c2_xlims, c2_ylims)

    return c1, c2


#def _generate_test_cubes_orig_flexi():
#    # create source test cube on rotated form
#    pole_lat = 53.4
#    pole_lon = -173.2
#    deg_swing = 35.3
#    pole_lon += deg_swing
##    c1_xvals = np.arange(-30.0, 30.1, 10.0) - deg_swing
##    c1_yvals = np.arange(-20.0, 20.1, 10.0)
#    c1_nx = 7
#    c1_ny = 5
#    c1_xlims = -60.0, 60.0
#    c1_ylims = -30.0, 30.0
#    scale_x = 1.0
#    scale_y = 1.0
#    c1_xlims = [x*scale_x for x in c1_xlims]
#    c1_ylims = [y*scale_y for y in c1_ylims]
#    do_wrapped = False
#    do_wrapped = True
#    if do_wrapped:
#        c1_xlims = [x+360.0 for x in c1_xlims]
#    c1_xvals = np.linspace(c1_xlims[0], c1_xlims[1], c1_nx)
#    c1_yvals = np.linspace(c1_ylims[0], c1_ylims[1], c1_ny)
#    c1_xvals -= deg_swing  # NB *approx* kludge !!  Only if close to -180.
#    c1_data = np.array([
#        [100, 100, 100, 100, 100, 100, 100],
#        [100, 199, 199, 199, 199, 100, 100],
#        [100, 100, 100, 199, 199, 100, 100],
#        [100, 100, 100, 199, 199, 199, 100],
#        [100, 100, 100, 100, 100, 100, 100]],
#        dtype=np.float)
#
#    c1 = iris.cube.Cube(c1_data)
#    c1_cs = iris.coord_systems.RotatedGeogCS(
#        grid_north_pole_latitude=pole_lat,
#        grid_north_pole_longitude=pole_lon)
#    c1_co_x = iris.coords.DimCoord(c1_xvals,
#                                   standard_name='grid_longitude',
#                                   units=iris.unit.Unit('degrees'),
#                                   coord_system=c1_cs)
#    c1.add_dim_coord(c1_co_x, 1)
#    c1_co_y = iris.coords.DimCoord(c1_yvals,
#                                   standard_name='grid_latitude',
#                                   units=iris.unit.Unit('degrees'),
#                                   coord_system=c1_cs)
#    c1.add_dim_coord(c1_co_y, 0)
#
#    # construct target cube to receive
#    nx2 = 10
#    ny2 = 8
#    c2_xlims = -150.0, 200.0
#    c2_ylims = -60.0, 90.0
#    do_min_covered = False
##    do_min_covered = True
#    if do_min_covered:
#        # this fixes the no-source-cells error problem
#        c2_xlims = -60.0, 90.0
#        c2_ylims = -10.0, 80.0
#    do_global = False
##    do_global = True
#    if do_global:
#        nx2 = 60
#        ny2 = 40
#        dx = 360.0/nx2
#        dy = 180.0/ny2
#        c2_xlims = -180.0 + 0.5 * dx, 180.0 - 0.5 * dx
#        c2_ylims = -90.0 + 0.5 * dy, 90.0 - 0.5 * dy
##    c2_xvals = np.arange(-45.0, 45.1, 10.0) # nx2=10
##    c2_yvals = np.arange(-10.0, 60.1, 10.0) # nx2=8
#    c2_xvals = np.linspace(c2_xlims[0], c2_xlims[1], nx2, endpoint=True)
#    c2_yvals = np.linspace(c2_ylims[0], c2_ylims[1], ny2, endpoint=False)
#    print 'c2_yvals:'
#    print c2_yvals
#    c2 = iris.cube.Cube(np.zeros((len(c2_yvals), len(c2_xvals))))
#    c2_cs = iris.coord_systems.GeogCS(6371229)
#    c2_co_x = iris.coords.DimCoord(c2_xvals,
#                                   standard_name='longitude',
#                                   units=iris.unit.Unit('degrees'),
#                                   coord_system=c2_cs)
#    c2.add_dim_coord(c2_co_x, 1)
#    c2_co_y = iris.coords.DimCoord(c2_yvals,
#                                   standard_name='latitude',
#                                   units=iris.unit.Unit('degrees'),
#                                   coord_system=c2_cs)
#    c2.add_dim_coord(c2_co_y, 0)
#
#    return c1, c2


class TestConservativeRegrid(tests.IrisTest):
    @classmethod
    def setUpClass(self):
        # Pre-initialise ESMF, just to avoid warnings about no logfile.
        # NOTE: noisy if logging off, and no control of filepath.  Boo !!
        self._emsf_logfile_path = os.path.join(os.getcwd(), 'ESMF_LogFile')
        ESMF.Manager(logkind=ESMF.LogKind.SINGLE, debug=False)

    @classmethod
    def tearDownClass(self):
        # remove the logfile if we can, just to be tidy
        if os.path.exists(self._emsf_logfile_path):
            os.remove(self._emsf_logfile_path)

    def test_simple_area_sum_preserved(self):
        shape1 = (5, 5)
        xlims1, ylims1 = ((-2, 2), (-2, 2))
        c1 = _make_test_cube(shape1, xlims1, ylims1)
        c1.data[:] = 0.0
        c1.data[2, 2] = 1.0

        shape2 = (4, 4)
        xlims2, ylims2 = ((-1.5, 1.5), (-1.5, 1.5))
        c2 = _make_test_cube(shape2, xlims2, ylims2)
        c2.data[:] = 0.0

        c1to2 = regrid_conservative_via_esmpy(c1, c2)
        d_expect = np.array([[0.00, 0.00, 0.00, 0.00],
                             [0.00, 0.25, 0.25, 0.00],
                             [0.00, 0.25, 0.25, 0.00],
                             [0.00, 0.00, 0.00, 0.00]])
        # Numbers are slightly off (~0.25000952).  This is expected.
        self.assertArrayAllClose(c1to2.data, d_expect, rtol=5.0e-5)
        sumAll = np.sum(c1to2.data)
        self.assertAlmostEqual(sumAll, 1.0, delta=0.00005)

        c1to2to1 = regrid_conservative_via_esmpy(c1to2, c1)
        d_expect = np.array([[0.0, 0.0000, 0.0000, 0.0000, 0.0],
                             [0.0, 0.0625, 0.1250, 0.0625, 0.0],
                             [0.0, 0.1250, 0.2500, 0.1250, 0.0],
                             [0.0, 0.0625, 0.1250, 0.0625, 0.0],
                             [0.0, 0.0000, 0.0000, 0.0000, 0.0]])
        # Errors now quite large
        self.assertArrayAllClose(c1to2to1.data, d_expect, atol=0.00002)
        sumAll = np.sum(c1to2to1.data)
        self.assertAlmostEqual(sumAll, 1.0, delta=0.00008)

    def test_polar_areas(self):
        # Like test_basic_area, but not symmetrical + bigger overall errors.
        shape1 = (5, 5)
        xlims1, ylims1 = ((-2, 2), (84, 88))
        c1 = _make_test_cube(shape1, xlims1, ylims1)
        c1.data[:] = 0.0
        c1.data[2, 2] = 1.0

        shape2 = (4, 4)
        xlims2, ylims2 = ((-1.5, 1.5), (84.5, 87.5))
        c2 = _make_test_cube(shape2, xlims2, ylims2)
        c2.data[:] = 0.0

        c1to2 = regrid_conservative_via_esmpy(c1, c2)
        d_expect = np.array([[0.0, 0.0, 0.0, 0.0],
                             [0.0, 0.23614, 0.23614, 0.0],
                             [0.0, 0.26784, 0.26784, 0.0],
                             [0.0, 0.0, 0.0, 0.0]])
        self.assertArrayAllClose(c1to2.data, d_expect, rtol=5.0e-5)
        sumAll = np.sum(c1to2.data)
        self.assertAlmostEqual(sumAll, 1.0, delta=0.008)

        c1to2to1 = regrid_conservative_via_esmpy(c1to2, c1)
        d_expect = np.array([[0.0, 0.0, 0.0, 0.0, 0.0],
                             [0.0, 0.056091, 0.112181, 0.056091, 0.0],
                             [0.0, 0.125499, 0.250998, 0.125499, 0.0],
                             [0.0, 0.072534, 0.145067, 0.072534, 0.0],
                             [0.0, 0.0, 0.0, 0.0, 0.0]])
        self.assertArrayAllClose(c1to2to1.data, d_expect, atol=0.0005)
        sumAll = np.sum(c1to2to1.data)
        self.assertAlmostEqual(sumAll, 1.0, delta=0.02)

    def test_fail_no_cs(self):
        shape1 = (5, 5)
        xlims1, ylims1 = ((-2, 2), (-2, 2))
        c1 = _make_test_cube(shape1, xlims1, ylims1)
        c1.data[:] = 0.0
        c1.data[2, 2] = 1.0

        shape2 = (4, 4)
        xlims2, ylims2 = ((-1.5, 1.5), (-1.5, 1.5))
        c2 = _make_test_cube(shape2, xlims2, ylims2)
        c2.data[:] = 0.0
        c2.coord('latitude').coord_system = None

        with self.assertRaises(ValueError):
            c1to2 = regrid_conservative_via_esmpy(c1, c2)

    def test_fail_different_cs(self):
        shape1 = (5, 5)
        xlims1, ylims1 = ((-2, 2), (-2, 2))
        c1 = _make_test_cube(shape1, xlims1, ylims1,
                             pole_latlon=(45.0, 35.0))
        c1.data[:] = 0.0
        c1.data[2, 2] = 1.0

        shape2 = (4, 4)
        xlims2, ylims2 = ((-1.5, 1.5), (-1.5, 1.5))
        c2 = _make_test_cube(shape2, xlims2, ylims2)
        c2.data[:] = 0.0
        c2.coord('latitude').coord_system = \
            c1.coord('grid_latitude').coord_system

        with self.assertRaises(ValueError):
            c1to2 = regrid_conservative_via_esmpy(c1, c2)


if __name__ == '__main__':
    tests.main()
