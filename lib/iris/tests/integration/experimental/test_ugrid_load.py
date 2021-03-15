# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Integration tests for NetCDF-UGRID file loading.

todo: fold these tests into netcdf tests when experimental.ugrid is folded into
 standard behaviour.

"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris import load, load_cube, NameConstraint
from iris.experimental.ugrid import PARSE_UGRID_ON_LOAD


def ugrid_load(*args, **kwargs):
    with PARSE_UGRID_ON_LOAD:
        return load(*args, **kwargs)


def ugrid_load_cube(*args, **kwargs):
    with PARSE_UGRID_ON_LOAD.context():
        return load_cube(*args, **kwargs)


@tests.skip_data
class TestBasic(tests.IrisTest):
    def test_2D_1t_face_half_levels(self):
        # TODO: remove constraint once file no longer has orphan connectivities.
        conv_rain = NameConstraint(var_name="conv_rain")
        cube = ugrid_load_cube(
            tests.get_data_path(
                [
                    "NetCDF",
                    "unstructured_grid",
                    "lfric_ngvat_2D_1t_face_half_levels_main_conv_rain.nc",
                ]
            ),
            constraint=conv_rain,
        )
        self.assertCML(
            cube, ("experimental", "ugrid", "2D_1t_face_half_levels.cml")
        )

    # def test_3D_1t_face_half_levels(self):
    #     pass
    #
    # def test_3D_1t_face_full_levels(self):
    #     pass
    #
    # def test_multiple_time_values(self):
    #     pass
    #
    # etc ...


# class TestPseudoLevels(tests.IrisTest):
#     pass
