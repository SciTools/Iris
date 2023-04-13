# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Integration tests for delayed saving.
"""
from datetime import datetime
import time
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
from iris.fileformats.netcdf.saver import SaverFillValueWarning
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
        include_extra_coordlikes=False,
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

        if include_extra_coordlikes:
            # Also concoct + attach an ancillary variable and a cell-measure, so we can
            #  check that they behave the same as coordinates.
            ancil_dims = [0, 2]
            cm_dims = [0, 3]
            ancil_shape = [cube.shape[idim] for idim in ancil_dims]
            cm_shape = [cube.shape[idim] for idim in cm_dims]
            from iris.coords import AncillaryVariable, CellMeasure

            ancil = AncillaryVariable(
                fix_array(np.zeros(ancil_shape)), long_name="sample_ancil"
            )
            cube.add_ancillary_variable(ancil, ancil_dims)
            cm = CellMeasure(
                fix_array(np.zeros(cm_shape)), long_name="sample_cm"
            )
            cube.add_cell_measure(cm, cm_dims)
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
        # NOTE: it might be nicer to use assertCDL, but unfortunately importing
        # unitest.TestCase seems to lose us the ability to use fixtures.

    @staticmethod
    def getmask(cube_or_coord):
        cube_or_coord = cube_or_coord.copy()  # avoid realising the original
        if hasattr(cube_or_coord, "points"):
            data = cube_or_coord.points
        else:
            data = cube_or_coord.data
        return np.ma.getmaskarray(data)

    def test_time_of_writing(
        self, save_is_delayed, output_path, scheduler_type
    ):
        # Check when lazy data is actually written :
        #  - in 'immediate' mode, on initial file write
        #  - in 'delayed' mode, only when delayed-write is executed.
        original_cube = self.make_testcube(include_extra_coordlikes=True)
        assert original_cube.has_lazy_data()
        assert original_cube.coord("surface_altitude").has_lazy_points()
        assert original_cube.cell_measure("sample_cm").has_lazy_data()
        assert original_cube.ancillary_variable("sample_ancil").has_lazy_data()

        return_saver_list = []
        result = iris.save(
            original_cube,
            output_path,
            compute=not save_is_delayed,
            return_saver_list=return_saver_list,
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
        ancil_mask = self.getmask(
            readback_cube.ancillary_variable("sample_ancil")
        )
        cm_mask = self.getmask(readback_cube.cell_measure("sample_cm"))
        if save_is_delayed:
            assert np.all(data_mask)
            assert np.all(coord_mask)
            assert np.all(ancil_mask)
            assert np.all(cm_mask)
        else:
            assert np.all(~data_mask)
            assert np.all(~coord_mask)
            assert np.all(~ancil_mask)
            assert np.all(~cm_mask)

        if save_is_delayed:
            saver = return_saver_list[0]
            assert len(saver._delayed_writes) != 0
            assert len(saver._delayed_writes) == 4
            result.compute()

            # shapes = [
            #     x.shape for x in (data_mask, coord_mask, ancil_mask, cm_mask)
            # ]
            # assert shapes == [
            #     (6, 70, 100, 100),
            #     (100, 100),
            #     (6, 100),
            #     (6, 100),
            # ]

            n_tries = 0
            all_done = False
            n_max_tries = 4
            retry_delay = 3.0
            start_time = datetime.now()
            while not all_done and n_tries < n_max_tries:
                n_tries += 1

                # Re-fetch the arrays.  The data is **no longer masked**.
                data_mask = self.getmask(readback_cube)
                coord_mask = self.getmask(
                    readback_cube.coord("surface_altitude")
                )
                ancil_mask = self.getmask(
                    readback_cube.ancillary_variable("sample_ancil")
                )
                cm_mask = self.getmask(readback_cube.cell_measure("sample_cm"))
                results = [
                    np.all(~x)
                    for x in (data_mask, coord_mask, ancil_mask, cm_mask)
                ]
                all_done = all(results)

                if not all_done:
                    time.sleep(retry_delay)

            # Perform a sequence of checks which should show what happened ...

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            print("time_of_writing, delayed-save test results:")
            print(
                f"  : all_done={all_done}, tries={n_tries}, elapsed-time={elapsed}"
            )

            # Check it either succeeded or timed out
            assert all_done or n_tries >= n_max_tries

            # Did it succeed? (if not must have retried)
            assert all_done

            # Did it work first time?
            assert n_tries == 1

            # assert np.all(~data_mask)
            # assert np.all(~coord_mask)
            # assert np.all(~ancil_mask)
            # assert np.all(~cm_mask)

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
            result_warnings = [
                log.message
                for log in logged_warnings
                if isinstance(log.message, SaverFillValueWarning)
            ]
        else:
            assert len(logged_warnings) == 0
            # Complete the operation now
            # NOTE: warnings should not be *issued* here, instead they are returned.
            warnings.simplefilter("error", category=SaverFillValueWarning)
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

    @classmethod
    @pytest.fixture(
        params=[
            "ThreadedScheduler",
            "DistributedScheduler",
            "SingleThreadScheduler",
        ]
    )
    def scheduler_type(cls, request):
        sched_typename = request.param
        if sched_typename == "ThreadedScheduler":
            config_name = "threads"
        elif sched_typename == "SingleThreadScheduler":
            config_name = "single-threaded"
        else:
            assert sched_typename == "DistributedScheduler"
            config_name = "distributed"

        if config_name == "distributed":
            _distributed_client = distributed.Client()

        with dask.config.set(scheduler=config_name):
            yield sched_typename

        if config_name == "distributed":
            _distributed_client.close()

    def test_scheduler_types(
        self, output_path, scheduler_type, save_is_delayed
    ):
        # Check operation works and behaves the same with different schedulers,
        # especially including distributed.

        # Just check that the dask scheduler is setup as 'expected'.
        if scheduler_type == "ThreadedScheduler":
            expected_dask_scheduler = "threads"
        elif scheduler_type == "SingleThreadScheduler":
            expected_dask_scheduler = "single-threaded"
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
