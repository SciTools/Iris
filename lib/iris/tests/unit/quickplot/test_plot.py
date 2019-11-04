# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for the `iris.quickplot.plot` function."""

from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests
from iris.tests.unit.plot import TestGraphicStringCoord

if tests.MPL_AVAILABLE:
    import iris.quickplot as qplt


@tests.skip_plot
class TestStringCoordPlot(TestGraphicStringCoord):
    def setUp(self):
        super().setUp()
        self.cube = self.cube[0, :]

    def test_yaxis_labels(self):
        qplt.plot(self.cube, self.cube.coord('str_coord'))
        self.assertBoundsTickLabels('yaxis')

    def test_xaxis_labels(self):
        qplt.plot(self.cube.coord('str_coord'), self.cube)
        self.assertBoundsTickLabels('xaxis')


if __name__ == "__main__":
    tests.main()
