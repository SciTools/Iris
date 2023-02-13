# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Integration tests covering thread safety during loading/saving netcdf files.

These tests are intended to catch non-thread-safe behaviour by producing CI
'irregularities' that are noticed and investigated. They cannot reliably
produce standard pytest failures, since the tools for 'correctly'
testing non-thread-safe behaviour are not available at the Python layer.
Thread safety problems can be either produce errors (like a normal test) OR
segfaults (test doesn't complete, pytest-xdiff starts a new test runner, the
end exit code is still non-0), and some problems do not occur in every test
run.

Token assertions are included after the line that is expected to reveal
a thread safety problem, as this seems to be good testing practice.

"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests  # isort:skip

from pathlib import Path

import dask
from dask import array as da
import numpy as np
import pytest

import iris
from iris.cube import Cube, CubeList


@pytest.fixture
def tiny_chunks():
    """Guarantee that Dask will use >1 thread by guaranteeing >1 chunk."""
    dask.config.set({"array.chunk-size": "1KiB"})

    def _check_tiny_loaded_chunks(cube: Cube):
        assert cube.has_lazy_data()
        cube_lazy_data = cube.core_data()
        assert np.product(cube_lazy_data.chunksize) < cube_lazy_data.size

    yield _check_tiny_loaded_chunks


@pytest.fixture
def save_common(tmp_path):
    save_path = tmp_path / "tmp.nc"

    def _func(cube: Cube):
        assert not save_path.exists()
        iris.save(cube, save_path)
        assert save_path.exists()

    yield _func


@pytest.fixture
def get_cubes_from_netcdf():
    load_dir_path = Path(tests.get_data_path(["NetCDF", "global", "xyt"]))
    loaded = iris.load(load_dir_path.glob("*"))
    smaller = CubeList([c[0, 0] for c in loaded])
    yield smaller


def test_load(tiny_chunks, get_cubes_from_netcdf):
    cube = get_cubes_from_netcdf[0]
    tiny_chunks(cube)
    _ = cube.data  # Any problems are expected here.
    assert not cube.has_lazy_data()


def test_save(tiny_chunks, save_common):
    cube = Cube(da.ones(1000))
    save_common(cube)  # Any problems are expected here.


def test_stream(tiny_chunks, get_cubes_from_netcdf, save_common):
    cube = get_cubes_from_netcdf[0]
    tiny_chunks(cube)
    save_common(cube)  # Any problems are expected here.


def test_stream_2_sources(get_cubes_from_netcdf, save_common):
    """Load from 2 sources to force Dask to use multiple threads."""
    cubes = get_cubes_from_netcdf
    final_cube = cubes[0] + cubes[1]
    save_common(final_cube)  # Any problems are expected here.


def test_comparison(get_cubes_from_netcdf):
    """
    Comparing two loaded files forces co-realisation.

    See :func:`iris._lazy_data._co_realise_lazy_arrays` .
    """
    cubes = get_cubes_from_netcdf
    _ = cubes[0] == cubes[1]  # Any problems are expected here.
    for cube in cubes:
        assert cube.has_lazy_data()
