# Copyright Iris Contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full licensing details.
"""Unit tests for :class:`iris.analysis.PointInCell`."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from unittest import mock

from iris.analysis import PointInCell


class Test_regridder(tests.IrisTest):
    def test(self):
        point_in_cell = PointInCell(mock.sentinel.weights)

        with mock.patch('iris.analysis.CurvilinearRegridder',
                        return_value=mock.sentinel.regridder) as ecr:
            regridder = point_in_cell.regridder(mock.sentinel.src,
                                                mock.sentinel.target)

        ecr.assert_called_once_with(mock.sentinel.src,
                                    mock.sentinel.target,
                                    mock.sentinel.weights)
        self.assertIs(regridder, mock.sentinel.regridder)


if __name__ == '__main__':
    tests.main()
