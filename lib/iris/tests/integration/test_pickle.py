# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Integration tests for pickling things."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import pickle
import unittest

import iris

if tests.GRIB_AVAILABLE:
    from iris_grib.message import GribMessage


class Common:
    def pickle_cube(self, protocol):
        # Ensure that data proxies are pickleable.
        cube = iris.load(self.path)[0]
        with self.temp_filename(".pkl") as filename:
            with open(filename, "wb") as f:
                pickle.dump(cube, f, protocol)
            with open(filename, "rb") as f:
                ncube = pickle.load(f)
        self.assertEqual(ncube, cube)

    def test_protocol_0(self):
        self.pickle_cube(0)

    def test_protocol_1(self):
        self.pickle_cube(1)

    def test_protocol_2(self):
        self.pickle_cube(2)


@tests.skip_data
@tests.skip_grib
class TestGribMessage(Common, tests.IrisTest):
    def setUp(self):
        self.path = tests.get_data_path(("GRIB", "fp_units", "hours.grib2"))

    def pickle_obj(self, obj):
        with self.temp_filename(".pkl") as filename:
            with open(filename, "wb") as f:
                pickle.dump(obj, f)

    # These probably "ought" to work, but currently fail.
    # see https://github.com/SciTools/iris/pull/2608
    @unittest.expectedFailure
    def test_protocol_0(self):
        super().test_protocol_0()

    @unittest.expectedFailure
    def test_protocol_1(self):
        super().test_protocol_1()

    @unittest.expectedFailure
    def test_protocol_2(self):
        super().test_protocol_2()

    def test(self):
        # Check that a GribMessage pickles without errors.
        messages = GribMessage.messages_from_filename(self.path)
        obj = next(messages)
        self.pickle_obj(obj)

    def test_data(self):
        # Check that GribMessage.data pickles without errors.
        messages = GribMessage.messages_from_filename(self.path)
        obj = next(messages).data
        self.pickle_obj(obj)


@tests.skip_data
class test_netcdf(Common, tests.IrisTest):
    def setUp(self):
        self.path = tests.get_data_path(
            ("NetCDF", "global", "xyt", "SMALL_hires_wind_u_for_ipcc4.nc")
        )


@tests.skip_data
class test_pp(Common, tests.IrisTest):
    def setUp(self):
        self.path = tests.get_data_path(("PP", "aPPglob1", "global.pp"))


@tests.skip_data
class test_ff(Common, tests.IrisTest):
    def setUp(self):
        self.path = tests.get_data_path(("FF", "n48_multi_field"))


if __name__ == "__main__":
    tests.main()
