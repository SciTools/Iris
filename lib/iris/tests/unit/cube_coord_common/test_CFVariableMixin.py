# (C) British Crown Copyright 2019, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""
Unit tests for the :class:`iris._cube_coord_common.CFVariableMixin`.
"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris._cube_coord_common import CFVariableMixin


class Test_token(tests.IrisTest):
    def test_passthru_None(self):
        result = CFVariableMixin.token(None)
        self.assertIsNone(result)

    def test_fail_leading_underscore(self):
        result = CFVariableMixin.token('_nope')
        self.assertIsNone(result)

    def test_fail_leading_dot(self):
        result = CFVariableMixin.token('.nope')
        self.assertIsNone(result)

    def test_fail_leading_plus(self):
        result = CFVariableMixin.token('+nope')
        self.assertIsNone(result)

    def test_fail_leading_at(self):
        result = CFVariableMixin.token('@nope')
        self.assertIsNone(result)

    def test_fail_space(self):
        result = CFVariableMixin.token('nope nope')
        self.assertIsNone(result)

    def test_fail_colon(self):
        result = CFVariableMixin.token('nope:')
        self.assertIsNone(result)

    def test_pass_simple(self):
        token = 'simple'
        result = CFVariableMixin.token(token)
        self.assertEqual(result, token)

    def test_pass_leading_digit(self):
        token = '123simple'
        result = CFVariableMixin.token(token)
        self.assertEqual(result, token)

    def test_pass_mixture(self):
        token = 'S.imple@one+two_3'
        result = CFVariableMixin.token(token)
        self.assertEqual(result, token)


class Test_name(tests.IrisTest):
    def setUp(self):
        # None token CFVariableMixin
        self.cf_var = CFVariableMixin()
        self.cf_var.standard_name = None
        self.cf_var.long_name = None
        self.cf_var.var_name = None
        self.cf_var.attributes = {}
        self.default = 'unknown'
        # bad token CFVariableMixin
        self.cf_bad = CFVariableMixin()
        self.cf_bad.standard_name = None
        self.cf_bad.long_name = 'nope nope'
        self.cf_bad.var_name = None
        self.cf_bad.attributes = {'STASH': 'nope nope'}

    def test_standard_name(self):
        token = 'air_temperature'
        self.cf_var.standard_name = token
        result = self.cf_var.name()
        self.assertEqual(result, token)

    def test_long_name(self):
        token = 'long_name'
        self.cf_var.long_name = token
        result = self.cf_var.name()
        self.assertEqual(result, token)

    def test_var_name(self):
        token = 'var_name'
        self.cf_var.var_name = token
        result = self.cf_var.name()
        self.assertEqual(result, token)

    def test_stash(self):
        token = 'stash'
        self.cf_var.var_name = token
        result = self.cf_var.name()
        self.assertEqual(result, token)

    def test_default(self):
        result = self.cf_var.name()
        self.assertEqual(result, self.default)

    def test_token_long_name(self):
        token = 'long_name'
        self.cf_bad.long_name = token
        result = self.cf_bad.name(token=True)
        self.assertEqual(result, token)

    def test_token_var_name(self):
        token = 'var_name'
        self.cf_bad.var_name = token
        result = self.cf_bad.name(token=True)
        self.assertEqual(result, token)

    def test_token_stash(self):
        token = 'stash'
        self.cf_bad.attributes['STASH'] = token
        result = self.cf_bad.name(token=True)
        self.assertEqual(result, token)

    def test_token_default(self):
        result = self.cf_var.name(token=True)
        self.assertEqual(result, self.default)

    def test_fail_token_default(self):
        cf_var = CFVariableMixin()
        cf_var.standard_name = None
        cf_var.long_name = None
        cf_var.var_name = None
        cf_var.attributes = {}

        emsg = 'Cannot retrieve a valid name token'
        with self.assertRaisesRegexp(ValueError, emsg):
            cf_var.name(default='_nope', token=True)


if __name__ == '__main__':
    tests.main()
