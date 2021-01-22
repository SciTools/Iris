# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for the :mod:`iris._representation` module."""

import numpy as np
import iris.tests as tests
import iris._representation
from iris.cube import Cube
from iris.coords import (
    DimCoord,
    AuxCoord,
    CellMeasure,
    AncillaryVariable,
    CellMethod,
)


def example_cube():
    cube = Cube(
        np.arange(6).reshape([3, 2]),
        standard_name="air_temperature",
        long_name="screen_air_temp",
        var_name="airtemp",
        units="K",
    )
    lat = DimCoord([0, 1, 2], standard_name="latitude", units="degrees")
    cube.add_dim_coord(lat, 0)
    return cube


class Test_CubeSummary(tests.IrisTest):
    def setUp(self):
        self.cube = example_cube()

    def test_header(self):
        rep = iris._representation.CubeSummary(self.cube)
        header_left = rep.header.nameunit
        header_right = rep.header.dimension_header.contents

        self.assertEqual(header_left, "air_temperature / (K)")
        self.assertEqual(header_right, ["latitude: 3", "-- : 2"])

    def test_vector_coord(self):
        rep = iris._representation.CubeSummary(self.cube)
        dim_section = rep.dim_coord_section

        self.assertEqual(len(dim_section.contents), 1)

        dim_summary = dim_section.contents[0]

        name = dim_summary.name
        dim_chars = dim_summary.dim_chars
        extra = dim_summary.extra

        self.assertEqual(name, "latitude")
        self.assertEqual(dim_chars, ["x", "-"])
        self.assertEqual(extra, "")

    def test_scalar_coord(self):
        cube = self.cube
        scalar_coord_no_bounds = AuxCoord([10], long_name="bar", units="K")
        scalar_coord_with_bounds = AuxCoord(
            [10], long_name="foo", units="K", bounds=[(5, 15)]
        )
        scalar_coord_text = AuxCoord(
            ["a\nb\nc"], long_name="foo", attributes={"key": "value"}
        )
        cube.add_aux_coord(scalar_coord_no_bounds)
        cube.add_aux_coord(scalar_coord_with_bounds)
        cube.add_aux_coord(scalar_coord_text)
        rep = iris._representation.CubeSummary(cube)

        scalar_section = rep.scalar_section

        self.assertEqual(len(scalar_section.contents), 3)

        no_bounds_summary = scalar_section.contents[0]
        bounds_summary = scalar_section.contents[1]
        text_summary = scalar_section.contents[2]

        self.assertEqual(no_bounds_summary.name, "bar")
        self.assertEqual(no_bounds_summary.content, "10 K")
        self.assertEqual(no_bounds_summary.extra, "")

        self.assertEqual(bounds_summary.name, "foo")
        self.assertEqual(bounds_summary.content, "10 K, bound=(5, 15) K")
        self.assertEqual(bounds_summary.extra, "")

        self.assertEqual(text_summary.name, "foo")
        self.assertEqual(text_summary.content, "a\nb\nc")
        self.assertEqual(text_summary.extra, "key='value'")


if __name__ == "__main__":
    tests.main()
