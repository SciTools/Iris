# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Cubesphere-like netcdf saving benchmarks.

Where possible benchmarks should be parameterised for two sizes of input data:
  * minimal: enables detection of regressions in parts of the run-time that do
             NOT scale with data size.
  * large: large enough to exclusively detect regressions in parts of the
           run-time that scale with data size. Aim for benchmark time ~20x
           that of the minimal benchmark.

"""
from iris import save
from iris.experimental.ugrid import save_mesh

from . import TrackAddedMemoryAllocation
from .generate_data.ugrid import make_cube_like_2d_cubesphere


class NetcdfSave:
    params = [[1, 600], [False, True]]
    param_names = ["cubesphere-N", "is_unstructured"]

    def setup(self, n_cubesphere, is_unstructured):
        self.cube = make_cube_like_2d_cubesphere(
            n_cube=n_cubesphere, with_mesh=is_unstructured
        )

    def _save_data(self, cube, do_copy=True):
        if do_copy:
            # Copy the cube, to avoid distorting the results by changing it
            # Because we known that older Iris code realises lazy coords
            cube = cube.copy()
        save(cube, "tmp.nc")

    def _save_mesh(self, cube):
        # In this case, we are happy that the mesh is *not* modified
        save_mesh(cube.mesh, "mesh.nc")

    def time_netcdf_save_cube(self, n_cubesphere, is_unstructured):
        self._save_data(self.cube)

    def time_netcdf_save_mesh(self, n_cubesphere, is_unstructured):
        if is_unstructured:
            self._save_mesh(self.cube)

    def track_addedmem_netcdf_save(self, n_cubesphere, is_unstructured):
        cube = self.cube.copy()  # Do this outside the testing block
        with TrackAddedMemoryAllocation() as mb:
            self._save_data(cube, do_copy=False)
        return mb.addedmem_mb()


# Declare a 'Mb' unit for all 'track_addedmem_..' type benchmarks
for attr in dir(NetcdfSave):
    if attr.startswith("track_addedmem_"):
        getattr(NetcdfSave, attr).unit = "Mb"
