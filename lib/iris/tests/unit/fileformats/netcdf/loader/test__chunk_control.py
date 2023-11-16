# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Integration tests for loading and saving netcdf files."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests  # isort:skip

from unittest.mock import ANY, patch

import dask
import pytest

import iris
from iris.fileformats.netcdf import loader
from iris.fileformats.netcdf.loader import CHUNK_CONTROL
from iris.cube import CubeList
import iris.tests.stock as istk


@pytest.fixture()
def save_cubelist_with_sigma(tmp_filepath):
    cube = istk.simple_4d_with_hybrid_height()
    cube_varname = "my_var"
    sigma_varname = "my_sigma"
    cube.var_name = cube_varname
    cube.coord("sigma").var_name = sigma_varname
    cube.coord("sigma").guess_bounds()
    iris.save(cube, tmp_filepath)
    return cube_varname, sigma_varname


@pytest.fixture
def save_cube_with_chunksize(tmp_filepath):
    iris.save(istk.simple_3d(), tmp_filepath, chunksizes=(1, 3, 4))


# @pytest.fixture
# def tmp_filepath():
#     tmp_dir = Path(tempfile.mkdtemp())
#     tmp_path = tmp_dir / "tmp.nc"
#     yield str(tmp_path)
#     shutil.rmtree(tmp_dir)

@pytest.fixture(scope="session")
def tmp_filepath(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("data")
    tmp_path = tmp_dir / "tmp.nc"
    yield str(tmp_path)



@pytest.fixture(autouse=True)
def remove_min_bytes():
    old_min_bytes = loader._LAZYVAR_MIN_BYTES
    loader._LAZYVAR_MIN_BYTES = 0
    yield
    loader._LAZYVAR_MIN_BYTES = old_min_bytes


def test_default(tmp_filepath, save_cubelist_with_sigma):
    cube_varname, _ = save_cubelist_with_sigma
    cubes = CubeList(loader.load_cubes(tmp_filepath))
    cube = cubes.extract_cube(cube_varname)
    assert cube.shape == (3, 4, 5, 6)
    assert cube.lazy_data().chunksize == (3, 4, 5, 6)

    sigma = cube.coord("sigma")
    assert sigma.shape == (4,)
    assert sigma.lazy_points().chunksize == (4,)
    assert sigma.lazy_bounds().chunksize == (4, 2)


def test_control_global(tmp_filepath, save_cubelist_with_sigma):
    cube_varname, _ = save_cubelist_with_sigma
    with CHUNK_CONTROL.set(model_level_number=2):
        cubes = CubeList(loader.load_cubes(tmp_filepath))
        cube = cubes.extract_cube(cube_varname)
    assert cube.shape == (3, 4, 5, 6)
    assert cube.lazy_data().chunksize == (3, 2, 5, 6)

    sigma = cube.coord("sigma")
    assert sigma.shape == (4,)
    assert sigma.lazy_points().chunksize == (2,)
    assert sigma.lazy_bounds().chunksize == (2, 2)


def test_control_sigma_only(tmp_filepath, save_cubelist_with_sigma):
    cube_varname, sigma_varname = save_cubelist_with_sigma
    with CHUNK_CONTROL.set(sigma_varname, model_level_number=2):
        cubes = CubeList(loader.load_cubes(tmp_filepath))
        cube = cubes.extract_cube(cube_varname)
    assert cube.shape == (3, 4, 5, 6)
    assert cube.lazy_data().chunksize == (3, 4, 5, 6)

    sigma = cube.coord("sigma")
    assert sigma.shape == (4,)
    assert sigma.lazy_points().chunksize == (2,)
    # N.B. this does not apply to bounds array
    assert sigma.lazy_bounds().chunksize == (4, 2)


def test_control_cube_var(tmp_filepath, save_cubelist_with_sigma):
    cube_varname, _ = save_cubelist_with_sigma
    with CHUNK_CONTROL.set(cube_varname, model_level_number=2):
        cubes = CubeList(loader.load_cubes(tmp_filepath))
        cube = cubes.extract_cube(cube_varname)
    assert cube.shape == (3, 4, 5, 6)
    assert cube.lazy_data().chunksize == (3, 2, 5, 6)

    sigma = cube.coord("sigma")
    assert sigma.shape == (4,)
    assert sigma.lazy_points().chunksize == (2,)
    assert sigma.lazy_bounds().chunksize == (2, 2)


def test_control_multiple(tmp_filepath, save_cubelist_with_sigma):
    cube_varname, sigma_varname = save_cubelist_with_sigma
    with CHUNK_CONTROL.set(
        cube_varname, model_level_number=2
    ), CHUNK_CONTROL.set(sigma_varname, model_level_number=3):
        cubes = CubeList(loader.load_cubes(tmp_filepath))
        cube = cubes.extract_cube(cube_varname)
    assert cube.shape == (3, 4, 5, 6)
    assert cube.lazy_data().chunksize == (3, 2, 5, 6)

    sigma = cube.coord("sigma")
    assert sigma.shape == (4,)
    assert sigma.lazy_points().chunksize == (3,)
    assert sigma.lazy_bounds().chunksize == (2, 2)


def test_neg_one(tmp_filepath, save_cubelist_with_sigma):
    cube_varname, _ = save_cubelist_with_sigma
    with dask.config.set({"array.chunk-size": "50B"}):
        with CHUNK_CONTROL.set(model_level_number=-1):
            cubes = CubeList(loader.load_cubes(tmp_filepath))
            cube = cubes.extract_cube(cube_varname)
    assert cube.shape == (3, 4, 5, 6)
    # uses known good output
    assert cube.lazy_data().chunksize == (1, 4, 1, 1)

    sigma = cube.coord("sigma")
    assert sigma.shape == (4,)
    assert sigma.lazy_points().chunksize == (4,)
    assert sigma.lazy_bounds().chunksize == (4, 1)


def test_from_file(tmp_filepath, save_cube_with_chunksize):
    with CHUNK_CONTROL.from_file():
        cube = next(loader.load_cubes(tmp_filepath))
    assert cube.shape == (2, 3, 4)
    assert cube.lazy_data().chunksize == (1, 3, 4)


def test_as_dask(tmp_filepath, save_cubelist_with_sigma):
    message = "Mock called, rest of test unneeded"
    with patch("iris.fileformats.netcdf.loader.as_lazy_data") as optimum:
        optimum.side_effect = RuntimeError(message)
        with CHUNK_CONTROL.as_dask():
            try:
                CubeList(loader.load_cubes(tmp_filepath))
            except RuntimeError as e:
                if str(e) != message:
                    raise e
        optimum.assert_called_with(
            ANY, chunks=None, dask_chunking=True
        )


if __name__ == "__main__":
    tests.main()
