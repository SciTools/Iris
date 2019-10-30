# Copyright Iris Contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full licensing details.
"""
Unit tests for the :class:`iris.coords.CellMethod`.
"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris._cube_coord_common import CFVariableMixin
from iris.coords import CellMethod, Coord


class Test(tests.IrisTest):
    def setUp(self):
        self.method = 'mean'

    def _check(self, token, coord, default=False):
        result = CellMethod(self.method, coords=coord)
        token = token if not default else CFVariableMixin._DEFAULT_NAME
        expected = '{}: {}'.format(self.method, token)
        self.assertEqual(str(result), expected)

    def test_coord_standard_name(self):
        token = 'air_temperature'
        coord = Coord(1, standard_name=token)
        self._check(token, coord)

    def test_coord_long_name(self):
        token = 'long_name'
        coord = Coord(1, long_name=token)
        self._check(token, coord)

    def test_coord_long_name_default(self):
        token = 'long name'  # includes space
        coord = Coord(1, long_name=token)
        self._check(token, coord, default=True)

    def test_coord_var_name(self):
        token = 'var_name'
        coord = Coord(1, var_name=token)
        self._check(token, coord)

    def test_coord_var_name_fail(self):
        token = 'var name'  # includes space
        emsg = 'is not a valid NetCDF variable name'
        with self.assertRaisesRegexp(ValueError, emsg):
            Coord(1, var_name=token)

    def test_coord_stash(self):
        token = 'stash'
        coord = Coord(1, attributes=dict(STASH=token))
        self._check(token, coord)

    def test_coord_stash_default(self):
        token = '_stash'  # includes leading underscore
        coord = Coord(1, attributes=dict(STASH=token))
        self._check(token, coord, default=True)

    def test_string(self):
        token = 'air_temperature'
        result = CellMethod(self.method, coords=token)
        expected = '{}: {}'.format(self.method, token)
        self.assertEqual(str(result), expected)

    def test_string_default(self):
        token = 'air temperature'  # includes space
        result = CellMethod(self.method, coords=token)
        expected = '{}: unknown'.format(self.method)
        self.assertEqual(str(result), expected)

    def test_mixture(self):
        token = 'air_temperature'
        coord = Coord(1, standard_name=token)
        result = CellMethod(self.method, coords=[coord, token])
        expected = '{}: {}, {}'.format(self.method, token, token)
        self.assertEqual(str(result), expected)

    def test_mixture_default(self):
        token = 'air temperature'  # includes space
        coord = Coord(1, long_name=token)
        result = CellMethod(self.method, coords=[coord, token])
        expected = '{}: unknown, unknown'.format(self.method, token, token)
        self.assertEqual(str(result), expected)


if __name__ == '__main__':
    tests.main()
