# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for the :class:`iris.coord_systems.RotatedMercator` class."""

from iris.coord_systems import RotatedMercator

from . import test_ObliqueMercator


class TestArgs(test_ObliqueMercator.TestArgs):
    class_kwargs_default = dict(
        latitude_of_projection_origin=0.0,
        longitude_of_projection_origin=0.0,
    )
    cartopy_kwargs_default = dict(
        central_longitude=0.0,
        central_latitude=0.0,
        false_easting=0.0,
        false_northing=0.0,
        scale_factor=1.0,
        azimuth=90.0,
        globe=None,
    )

    def make_instance(self) -> RotatedMercator:
        kwargs = self.class_kwargs
        kwargs.pop("azimuth_of_central_line", None)
        return RotatedMercator(**kwargs)
