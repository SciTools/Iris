# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""Test function :func:`iris.fileformats._nc_load_rules.helpers.\
build_auxilliary_coordinate`.

"""
# import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests  # isort:skip

import contextlib
from unittest import mock

import numpy as np
import pytest

from iris.coords import AuxCoord
from iris.exceptions import CannotAddError
from iris.fileformats._nc_load_rules.helpers import build_auxiliary_coordinate
from iris.fileformats.cf import CFVariable
from iris.fileformats.netcdf import _thread_safe_nc as threadsafe_nc


class TestBoundsVertexDim(tests.IrisTest):
    # Lookup for various tests (which change the dimension order).
    dim_names_lens = {
        "foo": 2,
        "bar": 3,
        "nv": 4,
        # 'x' and 'y' used as aliases for 'foo' and 'bar'
        "x": 2,
        "y": 3,
    }

    def setUp(self):
        # Create coordinate cf variables and pyke engine.
        dimension_names = ("foo", "bar")
        points, cf_data = self._make_array_and_cf_data(dimension_names)
        self.cf_coord_var = mock.Mock(
            spec=CFVariable,
            dimensions=dimension_names,
            cf_name="wibble",
            cf_data=cf_data,
            standard_name=None,
            long_name="wibble",
            units="km",
            shape=points.shape,
            size=np.prod(points.shape),
            dtype=points.dtype,
            __getitem__=lambda self, key: points[key],
        )

        expected_bounds, _ = self._make_array_and_cf_data(
            dimension_names=("foo", "bar", "nv")
        )
        self.expected_coord = AuxCoord(
            self.cf_coord_var[:],
            long_name=self.cf_coord_var.long_name,
            var_name=self.cf_coord_var.cf_name,
            units=self.cf_coord_var.units,
            bounds=expected_bounds,
        )

        self.engine = mock.Mock(
            cube=mock.Mock(),
            cf_var=mock.Mock(dimensions=("foo", "bar"), cf_data=cf_data),
            filename="DUMMY",
            cube_parts=dict(coordinates=[]),
        )

        # Patch the deferred loading that prevents attempted file access.
        # This assumes that self.cf_bounds_var is defined in the test case.
        def patched__getitem__(proxy_self, keys):
            for var in (self.cf_coord_var, self.cf_bounds_var):
                if proxy_self.variable_name == var.cf_name:
                    return var[keys]
            raise RuntimeError()

        self.patch(
            "iris.fileformats.netcdf.NetCDFDataProxy.__getitem__",
            new=patched__getitem__,
        )

        # Patch the helper function that retrieves the bounds cf variable,
        # and a False flag for climatological.
        # This avoids the need for setting up further mocking of cf objects.
        def _get_per_test_bounds_var(_coord_unused):
            # Return the 'cf_bounds_var' created by the current test.
            return (self.cf_bounds_var, False)

        self.patch(
            "iris.fileformats._nc_load_rules.helpers.get_cf_bounds_var",
            new=_get_per_test_bounds_var,
        )

    @classmethod
    def _make_array_and_cf_data(cls, dimension_names, rollaxis=False):
        shape = tuple(cls.dim_names_lens[name] for name in dimension_names)
        cf_data = mock.MagicMock(_FillValue=None, spec=[])
        cf_data.chunking = mock.MagicMock(return_value=shape)
        data = np.arange(np.prod(shape), dtype=float)
        if rollaxis:
            shape = shape[1:] + (shape[0],)
            data = data.reshape(shape)
            data = np.rollaxis(data, -1)
        else:
            data = data.reshape(shape)
        return data, cf_data

    def _make_cf_bounds_var(self, dimension_names, rollaxis=False):
        # Create the bounds cf variable.
        bounds, cf_data = self._make_array_and_cf_data(
            dimension_names, rollaxis=rollaxis
        )
        bounds *= 1000  # Convert to metres.
        cf_bounds_var = mock.Mock(
            spec=CFVariable,
            dimensions=dimension_names,
            cf_name="wibble_bnds",
            cf_data=cf_data,
            units="m",
            shape=bounds.shape,
            size=np.prod(bounds.shape),
            dtype=bounds.dtype,
            __getitem__=lambda self, key: bounds[key],
        )

        return cf_bounds_var

    def _check_case(self, dimension_names, rollaxis=False):
        self.cf_bounds_var = self._make_cf_bounds_var(
            dimension_names, rollaxis=rollaxis
        )

        # Asserts must lie within context manager because of deferred loading.
        build_auxiliary_coordinate(self.engine, self.cf_coord_var)

        # Test that expected coord is built and added to cube.
        self.engine.cube.add_aux_coord.assert_called_with(self.expected_coord, [0, 1])

        # Test that engine.cube_parts container is correctly populated.
        expected_list = [(self.expected_coord, self.cf_coord_var.cf_name)]
        self.assertEqual(self.engine.cube_parts["coordinates"], expected_list)

    def test_fastest_varying_vertex_dim__normalise_bounds(self):
        # The usual order.
        self._check_case(dimension_names=("foo", "bar", "nv"))

    def test_slowest_varying_vertex_dim__normalise_bounds(self):
        # Bounds in the first (slowest varying) dimension.
        self._check_case(dimension_names=("nv", "foo", "bar"), rollaxis=True)

    def test_fastest_with_different_dim_names__normalise_bounds(self):
        # Despite the dimension names ('x', and 'y') differing from the coord's
        # which are 'foo' and 'bar' (as permitted by the cf spec),
        # this should still work because the vertex dim is the fastest varying.
        self._check_case(dimension_names=("x", "y", "nv"))


class TestDtype(tests.IrisTest):
    def setUp(self):
        # Create coordinate cf variables and pyke engine.
        points = np.arange(6).reshape(2, 3)
        cf_data = mock.MagicMock(_FillValue=None)
        cf_data.chunking = mock.MagicMock(return_value=points.shape)

        self.cf_coord_var = mock.Mock(
            spec=CFVariable,
            dimensions=("foo", "bar"),
            cf_name="wibble",
            cf_data=cf_data,
            standard_name=None,
            long_name="wibble",
            units="m",
            shape=points.shape,
            size=np.prod(points.shape),
            dtype=points.dtype,
            __getitem__=lambda self, key: points[key],
        )

        self.engine = mock.Mock(
            cube=mock.Mock(),
            cf_var=mock.Mock(dimensions=("foo", "bar")),
            filename="DUMMY",
            cube_parts=dict(coordinates=[]),
        )

    @contextlib.contextmanager
    def deferred_load_patch(self):
        def patched__getitem__(proxy_self, keys):
            if proxy_self.variable_name == self.cf_coord_var.cf_name:
                return self.cf_coord_var[keys]
            raise RuntimeError()

        # Fix for deferred load, *AND* avoid loading small variable data in real arrays.
        with mock.patch(
            "iris.fileformats.netcdf.NetCDFDataProxy.__getitem__",
            new=patched__getitem__,
        ):
            # While loading, "turn off" loading small variables as real data.
            with mock.patch("iris.fileformats.netcdf.loader._LAZYVAR_MIN_BYTES", 0):
                yield

    def test_scale_factor_add_offset_int(self):
        self.cf_coord_var.scale_factor = 3
        self.cf_coord_var.add_offset = 5

        with self.deferred_load_patch():
            build_auxiliary_coordinate(self.engine, self.cf_coord_var)

        coord, _ = self.engine.cube_parts["coordinates"][0]
        self.assertEqual(coord.dtype.kind, "i")

    def test_scale_factor_float(self):
        self.cf_coord_var.scale_factor = 3.0

        with self.deferred_load_patch():
            build_auxiliary_coordinate(self.engine, self.cf_coord_var)

        coord, _ = self.engine.cube_parts["coordinates"][0]
        self.assertEqual(coord.dtype.kind, "f")

    def test_add_offset_float(self):
        self.cf_coord_var.add_offset = 5.0

        with self.deferred_load_patch():
            build_auxiliary_coordinate(self.engine, self.cf_coord_var)

        coord, _ = self.engine.cube_parts["coordinates"][0]
        self.assertEqual(coord.dtype.kind, "f")


class TestCoordConstruction(tests.IrisTest):
    def setUp(self):
        # Create dummy pyke engine.
        self.engine = mock.Mock(
            cube=mock.Mock(),
            cf_var=mock.Mock(dimensions=("foo", "bar")),
            filename="DUMMY",
            cube_parts=dict(coordinates=[]),
        )

        points = np.arange(6)
        units = "days since 1970-01-01"
        self.cf_coord_var = mock.Mock(
            spec=threadsafe_nc.VariableWrapper,
            dimensions=("foo",),
            scale_factor=1,
            add_offset=0,
            cf_name="wibble",
            cf_data=mock.MagicMock(chunking=mock.Mock(return_value=None), spec=[]),
            standard_name=None,
            long_name="wibble",
            units=units,
            calendar=None,
            shape=points.shape,
            size=np.prod(points.shape),
            dtype=points.dtype,
            __getitem__=lambda self, key: points[key],
        )

        bounds = np.arange(12).reshape(6, 2)
        cf_data = mock.MagicMock(chunking=mock.Mock(return_value=None))
        # we want to mock the absence of flag attributes to helpers.get_attr_units
        # see https://docs.python.org/3/library/unittest.mock.html#deleting-attributes
        del cf_data.flag_values
        del cf_data.flag_masks
        del cf_data.flag_meanings
        self.cf_bounds_var = mock.Mock(
            spec=threadsafe_nc.VariableWrapper,
            dimensions=("x", "nv"),
            scale_factor=1,
            add_offset=0,
            cf_name="wibble_bnds",
            cf_data=cf_data,
            units=units,
            shape=bounds.shape,
            size=np.prod(bounds.shape),
            dtype=bounds.dtype,
            __getitem__=lambda self, key: bounds[key],
        )
        self.bounds = bounds

        # Create patch for deferred loading that prevents attempted
        # file access. This assumes that self.cf_coord_var and
        # self.cf_bounds_var are defined in the test case.
        def patched__getitem__(proxy_self, keys):
            for var in (self.cf_coord_var, self.cf_bounds_var):
                if proxy_self.variable_name == var.cf_name:
                    return var[keys]
            raise RuntimeError()

        self.patch(
            "iris.fileformats.netcdf.NetCDFDataProxy.__getitem__",
            new=patched__getitem__,
        )

        # Patch the helper function that retrieves the bounds cf variable.
        # This avoids the need for setting up further mocking of cf objects.
        self.use_climatology_bounds = False  # Set this when you need to.

        def get_cf_bounds_var(coord_var):
            return self.cf_bounds_var, self.use_climatology_bounds

        self.patch(
            "iris.fileformats._nc_load_rules.helpers.get_cf_bounds_var",
            new=get_cf_bounds_var,
        )

        # test_not_added() has been written in pytest-style, but the rest of
        #  the class is pending migration. Defining self.monkeypatch (not the
        #  typical practice in pure pytest) allows this transitional state.
        self.monkeypatch = pytest.MonkeyPatch()

    def check_case_aux_coord_construction(self, climatology=False):
        # Test a generic auxiliary coordinate, with or without
        # a climatological coord.
        self.use_climatology_bounds = climatology

        expected_coord = AuxCoord(
            self.cf_coord_var[:],
            long_name=self.cf_coord_var.long_name,
            var_name=self.cf_coord_var.cf_name,
            units=self.cf_coord_var.units,
            bounds=self.bounds,
            climatological=climatology,
        )

        build_auxiliary_coordinate(self.engine, self.cf_coord_var)

        # Test that expected coord is built and added to cube.
        self.engine.cube.add_aux_coord.assert_called_with(expected_coord, [0])

    def test_aux_coord_construction(self):
        self.check_case_aux_coord_construction(climatology=False)

    def test_aux_coord_construction__climatology(self):
        self.check_case_aux_coord_construction(climatology=True)

    def test_not_added(self):
        # Confirm that the coord will be skipped if a CannotAddError is raised
        #  when attempting to add.
        def mock_add_aux_coord(_, __):
            raise CannotAddError("foo")

        with self.monkeypatch.context() as m:
            m.setattr(self.engine.cube, "add_aux_coord", mock_add_aux_coord)
            with pytest.warns(match="coordinate not added to Cube: foo"):
                build_auxiliary_coordinate(self.engine, self.cf_coord_var)

        assert self.engine.cube_parts["coordinates"] == []


if __name__ == "__main__":
    tests.main()
