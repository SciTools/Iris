# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Integration tests for delayed saving.
"""
import warnings

from cf_units import Unit
import dask.array as da
import dask.config
from dask.delayed import Delayed
import distributed
import numpy as np
import pytest

import iris
from iris.fileformats.netcdf._thread_safe_nc import default_fillvals
import iris.tests
from iris.tests.stock import realistic_4d


class Test__lazy_stream_data:
    @pytest.fixture(autouse=True, scope="module")
    def output_path(self, tmp_path_factory):
        tmpdir = tmp_path_factory.mktemp("save_testfiles")
        self.temp_output_filepath = tmpdir / "tmp.nc"
        yield self.temp_output_filepath

    @staticmethod
    @pytest.fixture(params=[False, True], ids=["SaveImmediate", "SaveDelayed"])
    def save_is_delayed(request):
        return request.param

    @staticmethod
    def make_testcube(
        include_lazy_content=True,
        ensure_fillvalue_collision=False,
        data_is_maskedbytes=False,
    ):
        cube = realistic_4d()

        def fix_array(array):
            """
            Make a new, custom array to replace the provided cube/coord data.
            Optionally provide default-fill-value collisions, and/or replace with lazy
            content.
            """
            if array is not None:
                if data_is_maskedbytes:
                    dmin, dmax = 0, 255
                else:
                    dmin, dmax = array.min(), array.max()
                array = np.random.uniform(dmin, dmax, size=array.shape)

                if data_is_maskedbytes:
                    array = array.astype("u1")
                    array = np.ma.masked_array(array)
                    # To trigger, it must also have at least one *masked point*.
                    array[tuple([0] * array.ndim)] = np.ma.masked

                if ensure_fillvalue_collision:
                    # Set point at midpoint index = default-fill-value
                    fill_value = default_fillvals[array.dtype.str[1:]]
                    inds = tuple(dim // 2 for dim in array.shape)
                    array[inds] = fill_value

                if include_lazy_content:
                    # Make the array lazy.
                    # Ensure we always have multiple chunks (relatively small ones).
                    chunks = list(array.shape)
                    chunks[0] = 1
                    array = da.from_array(array, chunks=chunks)

            return array

        # Replace the cube data, and one aux-coord, according to the control settings.
        cube.data = fix_array(cube.data)
        auxcoord = cube.coord("surface_altitude")
        auxcoord.points = fix_array(auxcoord.points)
        return cube

    def test_realfile_loadsave_equivalence(self, save_is_delayed, output_path):
        input_filepath = iris.tests.get_data_path(
            ["NetCDF", "global", "xyz_t", "GEMS_CO2_Apr2006.nc"]
        )
        original_cubes = iris.load(input_filepath)

        # Pre-empt some standard changes that an iris save will impose.
        for cube in original_cubes:
            if cube.units == Unit("-"):
                # replace 'unknown unit' with 'no unit'.
                cube.units = Unit("?")
            # Fix conventions attribute to what iris.save outputs.
            cube.attributes["Conventions"] = "CF-1.7"

        original_cubes = sorted(original_cubes, key=lambda cube: cube.name())
        result = iris.save(
            original_cubes, output_path, compute=not save_is_delayed
        )
        if save_is_delayed:
            # In this case, must also "complete" the save.
            result.compute()
        reloaded_cubes = iris.load(output_path)
        reloaded_cubes = sorted(reloaded_cubes, key=lambda cube: cube.name())
        assert reloaded_cubes == original_cubes
        # NOTE: it might be nicer to do assertCDL, but I', not sure how to access that
        # from pytest-style test code ?

    @staticmethod
    def getmask(cube_or_coord):
        cube_or_coord = cube_or_coord.copy()  # avoid realising the original
        if hasattr(cube_or_coord, "points"):
            data = cube_or_coord.points
        else:
            data = cube_or_coord.data
        return np.ma.getmaskarray(data)

    def test_time_of_writing(self, save_is_delayed, output_path):
        # Check when lazy data is actually written :
        #  - in 'immediate' mode, on initial file write
        #  - in 'delayed' mode, only when delayed-write is executed.
        original_cube = self.make_testcube()
        assert original_cube.has_lazy_data()

        result = iris.save(
            original_cube, output_path, compute=not save_is_delayed
        )
        assert save_is_delayed == (result is not None)

        # Read back : NOTE must sidestep the separate surface-altitude cube.
        readback_cube = iris.load_cube(
            output_path, "air_potential_temperature"
        )
        assert readback_cube.has_lazy_data()

        # If 'delayed', the lazy content should all be masked, otherwise none of it.
        data_mask = self.getmask(readback_cube)
        coord_mask = self.getmask(readback_cube.coord("surface_altitude"))
        if save_is_delayed:
            assert np.all(data_mask)
            assert np.all(coord_mask)
        else:
            assert np.all(~data_mask)
            assert np.all(~coord_mask)

        if save_is_delayed:
            result.compute()
            # Re-fetch the arrays.  The data is **no longer masked**.
            data_mask = self.getmask(readback_cube)
            coord_mask = self.getmask(readback_cube.coord("surface_altitude"))
            assert np.all(~data_mask)
            assert np.all(~coord_mask)

    @pytest.mark.parametrize(
        "warning_type", ["WarnMaskedBytes", "WarnFillvalueCollision"]
    )
    def test_fill_warnings(self, warning_type, output_path, save_is_delayed):
        # Test collision warnings for data with fill-value collisions, or for masked
        # byte data.
        if warning_type == "WarnFillvalueCollision":
            make_fv_collide = True
            make_maskedbytes = False
            expected_msg = (
                "contains unmasked data points equal to the fill-value"
            )
        else:
            # warning_type == 'WarnMaskedBytes'
            make_fv_collide = False
            make_maskedbytes = True
            expected_msg = "contains byte data with masked points"

        cube = self.make_testcube(
            include_lazy_content=True,
            ensure_fillvalue_collision=make_fv_collide,
            data_is_maskedbytes=make_maskedbytes,
        )
        with warnings.catch_warnings(record=True) as logged_warnings:
            result = iris.save(cube, output_path, compute=not save_is_delayed)

        if not save_is_delayed:
            result_warnings = [log.message for log in logged_warnings]
        else:
            assert len(logged_warnings) == 0
            # Complete the operation now
            # NOTE: warnings should not be *issued* here, instead they are returned.
            warnings.simplefilter("error")
            result_warnings = result.compute()

        # Either way, we should now have 2 similar warnings.
        assert len(result_warnings) == 2
        assert all(
            expected_msg in warning.args[0] for warning in result_warnings
        )

    def test_no_delayed_writes(self, output_path):
        # Just check that a delayed save returns a usable 'delayed' object, even when
        # there is no lazy content = no delayed writes to perform.
        cube = self.make_testcube(include_lazy_content=False)
        warnings.simplefilter("error")
        result = iris.save(cube, output_path, compute=False)
        assert isinstance(result, Delayed)
        assert result.compute() == []

    _distributed_client = None

    @classmethod
    @pytest.fixture(params=["ThreadedScheduler", "DistributedScheduler"])
    def scheduler_type(cls, request):
        sched_typename = request.param
        if sched_typename == "ThreadedScheduler":
            config_name = "threads"
            if cls._distributed_client is not None:
                cls._distributed_client.close()
                cls._distributed_client = None
        else:
            config_name = "distributed"
            if cls._distributed_client is None:
                cls._distributed_client = distributed.Client()

        with dask.config.set(scheduler=config_name):
            yield sched_typename

    def test_distributed(self, output_path, scheduler_type, save_is_delayed):
        # Check operation works, and behaves the same, with a distributed scheduler.

        # Just check that the dask scheduler is setup as 'expected'.
        if scheduler_type == "ThreadedScheduler":
            expected_dask_scheduler = "threads"
        else:
            assert scheduler_type == "DistributedScheduler"
            expected_dask_scheduler = "distributed"
        assert dask.config.get("scheduler") == expected_dask_scheduler

        # Use a testcase that produces delayed warnings.
        cube = self.make_testcube(
            include_lazy_content=True, ensure_fillvalue_collision=True
        )
        with warnings.catch_warnings(record=True) as logged_warnings:
            result = iris.save(cube, output_path, compute=not save_is_delayed)

        if not save_is_delayed:
            assert result is None
            assert len(logged_warnings) == 2
            issued_warnings = [log.message for log in logged_warnings]
        else:
            assert result is not None
            assert len(logged_warnings) == 0
            warnings.simplefilter("error")
            issued_warnings = result.compute()

        assert len(issued_warnings) == 2
        expected_msg = "contains unmasked data points equal to the fill-value"
        assert all(
            expected_msg in warning.args[0] for warning in issued_warnings
        )
