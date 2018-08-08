# (C) British Crown Copyright 2010 - 2018, Met Office
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

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six

# import iris tests first so that some things can be initialised before importing anything else
import iris.tests as tests

import os
import tempfile

import cf_units
import cftime
import numpy as np

import iris.coords
import iris.coord_systems
import iris.fileformats.pp
from iris.fileformats.pp import PPField3
from iris.tests import mock
import iris.tests.pp as pp
import iris.util
import iris.tests.stock as stock


def itab_callback(cube, field, filename):
    cube.add_aux_coord(iris.coords.AuxCoord([field.lbrel], long_name='MOUMHeaderReleaseNumber', units='no_unit')) 
    cube.add_aux_coord(iris.coords.AuxCoord([field.lbexp], long_name='ExperimentNumber(ITAB)', units='no_unit')) 


@tests.skip_data
class TestPPSave(tests.IrisTest, pp.PPTest):
    def test_no_forecast_time(self):
        cube = stock.lat_lon_cube()
        coord = iris.coords.DimCoord(np.array([24], dtype=np.int64),
                                     standard_name='time',
                                     units='hours since epoch')
        cube.add_aux_coord(coord)
        self.assertCML(cube, ['cube_to_pp', 'no_forecast_time.cml'])

        reference_txt_path = tests.get_result_path(('cube_to_pp', 'no_forecast_time.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=cube) as temp_pp_path:
            iris.save(cube, temp_pp_path)

    def test_no_forecast_period(self):
        cube = stock.lat_lon_cube()
        # Add a bounded scalar time coord and a forecast_reference_time.
        time_coord = iris.coords.DimCoord(
            10.958333, standard_name='time',
            units='days since 2013-05-10 12:00',
            bounds=[10.916667, 11.0])
        cube.add_aux_coord(time_coord)
        forecast_reference_time = iris.coords.DimCoord(
            2.0, standard_name='forecast_reference_time',
            units='weeks since 2013-05-07')
        cube.add_aux_coord(forecast_reference_time)

        self.assertCML(cube, ['cube_to_pp', 'no_forecast_period.cml'])
        reference_txt_path = tests.get_result_path(('cube_to_pp',
                                                    'no_forecast_period.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=cube) as \
                temp_pp_path:
            iris.save(cube, temp_pp_path)

    def test_pp_save_rules(self):
        # Test pp save rules without user rules.

        #read
        in_filename = tests.get_data_path(('PP', 'simple_pp', 'global.pp'))
        cubes = iris.load(in_filename, callback=itab_callback)

        reference_txt_path = tests.get_result_path(('cube_to_pp', 'simple.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=cubes) as temp_pp_path:
            iris.save(cubes, temp_pp_path)

    def test_pp_append_singles(self):
        # Test pp append saving - single cubes.
        
        # load 2 arrays of >2D cubes
        cube = stock.simple_pp()
        
        reference_txt_path = tests.get_result_path(('cube_to_pp', 'append_single.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=[cube, cube]) as temp_pp_path:
            iris.save(cube, temp_pp_path)                # Create file
            iris.save(cube, temp_pp_path, append=True)   # Append to file

        reference_txt_path = tests.get_result_path(('cube_to_pp', 'replace_single.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=cube) as temp_pp_path:
            iris.save(cube, temp_pp_path)                # Create file
            iris.save(cube, temp_pp_path)                # Replace file

    def test_pp_append_lists(self):
        # Test PP append saving - lists of cubes.
        # For each of the first four time-steps in the 4D cube,
        # pull out the bottom two levels.
        cube_4d = stock.realistic_4d()
        cubes = [cube_4d[i, :2, :, :] for i in range(4)]

        reference_txt_path = tests.get_result_path(('cube_to_pp', 'append_multi.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=cubes) as temp_pp_path:
            iris.save(cubes[:2], temp_pp_path)
            iris.save(cubes[2:], temp_pp_path, append=True)

        reference_txt_path = tests.get_result_path(('cube_to_pp', 'replace_multi.txt'))
        with self.cube_save_test(reference_txt_path, reference_cubes=cubes[2:]) as temp_pp_path:
            iris.save(cubes[:2], temp_pp_path)
            iris.save(cubes[2:], temp_pp_path)

    def add_coords_to_cube_and_test(self, coord1, coord2):
        # a wrapper for creating arbitrary 2d cross-sections and run pp-saving tests
        dataarray = np.arange(16, dtype='>f4').reshape(4, 4)
        cm = iris.cube.Cube(data=dataarray)

        cm.add_dim_coord(coord1, 0)
        cm.add_dim_coord(coord2, 1)
        
        # TODO: This is the desired line of code...
        # reference_txt_path = tests.get_result_path(('cube_to_pp', '%s.%s.pp.txt' % (coord1.name(), coord2.name())))
        # ...but this is required during the CF change, to maintain the original filename.
        coord1_name = coord1.name().replace("air_", "")
        coord2_name = coord2.name().replace("air_", "") 
        reference_txt_path = tests.get_result_path(('cube_to_pp', '%s.%s.pp.txt' % (coord1_name, coord2_name))) 

        # test with name
        with self.cube_save_test(reference_txt_path, reference_cubes=cm, 
                field_coords=[coord1.name(), coord2.name()]) as temp_pp_path:
            iris.save(cm, temp_pp_path, field_coords=[coord1.name(), coord2.name()])
        # test with coord
        with self.cube_save_test(reference_txt_path, reference_cubes=cm, 
                field_coords=[coord1, coord2]) as temp_pp_path:
            iris.save(cm, temp_pp_path, field_coords=[coord1, coord2])

    def test_non_standard_cross_sections(self):
        #ticket #1037, the five variants being dealt with are
        #    'pressure.latitude',
        #    'depth.latitude',
        #    'eta.latitude',
        #    'pressure.time',
        #    'depth.time',

        f = FakePPEnvironment()

        self.add_coords_to_cube_and_test(
            iris.coords.DimCoord(f.z, long_name='air_pressure', units='hPa', bounds=f.z_bounds),
            iris.coords.DimCoord(f.y, standard_name='latitude', units='degrees', bounds=f.y_bounds, coord_system=f.geog_cs()))
            
        self.add_coords_to_cube_and_test(
            iris.coords.DimCoord(f.z, long_name='depth', units='m', bounds=f.z_bounds),
            iris.coords.DimCoord(f.y, standard_name='latitude', units='degrees', bounds=f.y_bounds, coord_system=f.geog_cs()))
            
        self.add_coords_to_cube_and_test(
            iris.coords.DimCoord(f.z, long_name='eta', units='1', bounds=f.z_bounds),
            iris.coords.DimCoord(f.y, standard_name='latitude', units='degrees', bounds=f.y_bounds, coord_system=f.geog_cs()))
            
        self.add_coords_to_cube_and_test(
            iris.coords.DimCoord(f.z, long_name='air_pressure', units='hPa', bounds=f.z_bounds),
            iris.coords.DimCoord(f.y, standard_name='time', units=cf_units.Unit('days since 0000-01-01 00:00:00', calendar=cf_units.CALENDAR_360_DAY), bounds=f.y_bounds))
            
        self.add_coords_to_cube_and_test(
            iris.coords.DimCoord(f.z, standard_name='depth', units='m', bounds=f.z_bounds),
            iris.coords.DimCoord(f.y, standard_name='time', units=cf_units.Unit('days since 0000-01-01 00:00:00', calendar=cf_units.CALENDAR_360_DAY), bounds=f.y_bounds))

    def test_365_calendar_export(self):
        # test for 365 day calendar export
        cube = stock.simple_pp()
        new_unit = cf_units.Unit('hours since 1970-01-01 00:00:00',
                                  calendar=cf_units.CALENDAR_365_DAY)
        cube.coord('time').units = new_unit
        # Add an extra "fill_value" property, as used by the save rules.
        cube.fill_value = None
        pp_field = mock.MagicMock(spec=PPField3)
        iris.fileformats.pp_save_rules.verify(cube, pp_field)
        self.assertEqual(pp_field.lbtim.ic, 4)


class FakePPEnvironment(object):
    ''' fake a minimal PP environment for use in cross-section coords, as in PP save rules '''
    y = [1, 2, 3, 4]
    z = [111, 222, 333, 444]
    y_bounds = [[0.9, 1.1], [1.9, 2.1], [2.9, 3.1], [3.9, 4.1]]
    z_bounds = [[110.9, 111.1], [221.9, 222.1], [332.9, 333.1], [443.9, 444.1]]

    def geog_cs(self):
        """Return a GeogCS for this PPField.

        Returns:
            A GeogCS with the appropriate earth shape, meridian and pole position.
        """
        return iris.coord_systems.GeogCS(6371229.0)


class TestPPSaveRules(tests.IrisTest, pp.PPTest):
    def test_default_coord_system(self):
        GeogCS = iris.coord_systems.GeogCS
        cube = iris.tests.stock.lat_lon_cube()
        reference_txt_path = tests.get_result_path(('cube_to_pp',
                                                    'default_coord_system.txt'))
        # Remove all coordinate systems.
        for coord in cube.coords():
            coord.coord_system = None
        # Ensure no coordinate systems available.
        self.assertIsNone(cube.coord_system(GeogCS))
        self.assertIsNone(cube.coord_system(None))
        with self.cube_save_test(reference_txt_path, reference_cubes=cube) as \
                temp_pp_path:
            # Save cube to PP with no coordinate system.
            iris.save(cube, temp_pp_path)
            pp_cube = iris.load_cube(temp_pp_path)
            # Ensure saved cube has the default coordinate system.
            self.assertIsInstance(pp_cube.coord_system(GeogCS),
                                  iris.coord_systems.GeogCS)
            self.assertIsNotNone(pp_cube.coord_system(None))
            self.assertIsInstance(pp_cube.coord_system(None),
                                  iris.coord_systems.GeogCS)
            self.assertIsNotNone(pp_cube.coord_system())
            self.assertIsInstance(pp_cube.coord_system(),
                                  iris.coord_systems.GeogCS)

    def lbproc_from_pp(self, filename):
        # Gets the lbproc field from the ppfile
        pp_file = iris.fileformats.pp.load(filename)
        field = next(pp_file)
        return field.lbproc

    def test_pp_save_rules(self):
        # Test single process flags
        for _, process_desc in iris.fileformats.pp.LBPROC_PAIRS[1:]:
            # Get basic cube and set process flag manually
            ll_cube = stock.lat_lon_cube()
            ll_cube.attributes["ukmo__process_flags"] = (process_desc,)
    
            # Save cube to pp
            temp_filename = iris.util.create_temp_filename(".pp")
            iris.save(ll_cube, temp_filename)
     
            # Check the lbproc is what we expect
            self.assertEqual(self.lbproc_from_pp(temp_filename),
                             iris.fileformats.pp.lbproc_map[process_desc])

            os.remove(temp_filename)

        # Test mutiple process flags
        multiple_bit_values = ((128, 64), (4096, 1024), (8192, 1024))
        
        # Maps lbproc value to the process flags that should be created
        multiple_map = {sum(bits) : [iris.fileformats.pp.lbproc_map[bit] for bit in bits] for bits in multiple_bit_values}

        for lbproc, descriptions in six.iteritems(multiple_map):
            ll_cube = stock.lat_lon_cube()
            ll_cube.attributes["ukmo__process_flags"] = descriptions
            
            # Save cube to pp
            temp_filename = iris.util.create_temp_filename(".pp")
            iris.save(ll_cube, temp_filename)
            
            # Check the lbproc is what we expect
            self.assertEqual(self.lbproc_from_pp(temp_filename), lbproc)

            os.remove(temp_filename)

    @tests.skip_data
    def test_lbvc(self):
        cube = stock.realistic_4d_no_derived()[0, :4, ...]
        
        v_coord = iris.coords.DimCoord(standard_name='depth', 
                                       units='m', points=[-5, -10, -15, -20])
        
        cube.remove_coord('level_height')
        cube.remove_coord('sigma')
        cube.remove_coord('surface_altitude')
        cube.add_aux_coord(v_coord, 0)
    
        expected = ([2, 1, -5.0],
                    [2, 2, -10.0],
                    [2, 3, -15.0],
                    [2, 4, -20.0])
                    
        for field, (lbvc, lblev, blev) in zip(fields_from_cube(cube), expected):
            self.assertEqual(field.lbvc, lbvc)
            self.assertEqual(field.lblev, lblev)
            self.assertEqual(field.blev, blev)


class TestTimeMean(tests.IrisTest):
    '''
    Tests that time mean cell method is converted to pp appropriately.

    Pattern is pairs of tests - one with time mean method, and one without, to
    show divergent behaviour.

    '''
    def test_t1_time_mean(self):
        cube = _get_single_time_cube(set_time_mean=True)
        tc = cube.coord(axis='t')
        expected = tc.units.num2date(0)

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.t1

        self.assertEqual(expected, actual)

    def test_t1_no_time_mean(self):
        cube = _get_single_time_cube()
        tc = cube.coord(axis='t')
        expected = tc.units.num2date(15)

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.t1

        self.assertEqual(expected, actual)

    def test_t2_time_mean(self):
        cube = _get_single_time_cube(set_time_mean=True)
        tc = cube.coord(axis='t')
        expected = tc.units.num2date(30)

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.t2

        self.assertEqual(expected, actual)

    def test_t2_no_time_mean(self):
        cube = _get_single_time_cube(set_time_mean=False)
        expected = cftime.datetime(0, 0, 0)

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.t2
        self.assertEqual(expected, actual)

    def test_lbft_no_forecast_time(self):
        # Different pattern here: checking that lbft hasn't been changed from
        # the default value.
        cube = _get_single_time_cube()
        mock_lbft = mock.sentinel.lbft

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            pp_field.lbft = mock_lbft
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.lbft

        assert(mock_lbft is actual)

    def test_lbtim_no_time_mean(self):
        cube = _get_single_time_cube()
        expected_ib = 0
        expected_ic = 2  # 360 day calendar

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual_ib = pp_field.lbtim.ib
        actual_ic = pp_field.lbtim.ic

        self.assertEqual(expected_ib, actual_ib)
        self.assertEqual(expected_ic, actual_ic)

    def test_lbtim_time_mean(self):
        cube = _get_single_time_cube(set_time_mean=True)
        expected_ib = 2  # Time mean
        expected_ic = 2  # 360 day calendar

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual_ib = pp_field.lbtim.ib
        actual_ic = pp_field.lbtim.ic

        self.assertEqual(expected_ib, actual_ib)
        self.assertEqual(expected_ic, actual_ic)

    def test_lbproc_no_time_mean(self):
        cube = _get_single_time_cube()
        expected = 0

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.lbproc

        self.assertEqual(expected, actual)

    def test_lbproc_time_mean(self):
        cube = _get_single_time_cube(set_time_mean=True)
        expected = 128

        with mock.patch('iris.fileformats.pp.PPField3',
                        autospec=True) as pp_field:
            iris.fileformats.pp_save_rules.verify(cube, pp_field)
        actual = pp_field.lbproc

        self.assertEqual(expected, actual)


def _get_single_time_cube(set_time_mean=False):
    cube = stock.realistic_3d()[0:1, :, :]
    cube.remove_coord('time')
    cube.remove_coord('forecast_period')
    tc = iris.coords.DimCoord(
        points=[15, ],
        standard_name='time',
        units=cf_units.Unit('days since epoch', calendar='360_day'),
        bounds=[[0, 30], ],
    )
    cube.add_dim_coord(tc, 0)
    if set_time_mean:
        cube.cell_methods = (iris.coords.CellMethod("mean", coords='time'), )
    return cube


def fields_from_cube(cubes):
    """
    Return an iterator of PP fields generated from saving the given cube(s)
    to a temporary file, and then subsequently loading them again 
    """
    with tempfile.NamedTemporaryFile('w+b', suffix='.pp') as tmp_file:
        if six.PY2:
            fh = tmp_file.file
        else:
            fh = tmp_file
        iris.save(cubes, fh, saver='pp')
        
        # make sure the fh is written to disk, and move it back to the
        # start of the file 
        fh.flush()
        os.fsync(fh)        
        fh.seek(0)
        
        # load in the saved pp fields and check the appropriate metadata
        for field in iris.fileformats.pp.load(tmp_file.name):
            yield field
            

if __name__ == "__main__":
    tests.main()
    
