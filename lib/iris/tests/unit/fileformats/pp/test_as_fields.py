# Copyright Iris Contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for the `iris.fileformats.pp.as_fields` function."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris.coords import DimCoord
from iris.fileformats._ff_cross_references import STASH_TRANS
import iris.fileformats.pp as pp
import iris.tests.stock as stock


class TestAsFields(tests.IrisTest):
    def setUp(self):
        self.cube = stock.realistic_3d()

    def test_cube_only(self):
        fields = pp.as_fields(self.cube)
        for field in fields:
            self.assertEqual(field.lbcode, 101)

    def test_field_coords(self):
        fields = pp.as_fields(self.cube,
                              field_coords=['grid_longitude',
                                            'grid_latitude'])
        for field in fields:
            self.assertEqual(field.lbcode, 101)


if __name__ == "__main__":
    tests.main()
