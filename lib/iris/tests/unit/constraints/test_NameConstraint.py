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
"""Unit tests for the `iris._constraints.NameConstraint` class."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from unittest.mock import Mock, sentinel

from iris._constraints import NameConstraint


class Test___init__(tests.IrisTest):
    def setUp(self):
        self.default = 'none'

    def test_default(self):
        constraint = NameConstraint()
        self.assertEqual(constraint.standard_name, self.default)
        self.assertEqual(constraint.long_name, self.default)
        self.assertEqual(constraint.var_name, self.default)
        self.assertEqual(constraint.STASH, self.default)

    def test_standard_name(self):
        standard_name = sentinel.standard_name
        constraint = NameConstraint(standard_name=standard_name)
        self.assertEqual(constraint.standard_name, standard_name)
        constraint = NameConstraint(standard_name)
        self.assertEqual(constraint.standard_name, standard_name)

    def test_long_name(self):
        long_name = sentinel.long_name
        constraint = NameConstraint(long_name=long_name)
        self.assertEqual(constraint.standard_name, self.default)
        self.assertEqual(constraint.long_name, long_name)
        constraint = NameConstraint(None, long_name)
        self.assertIsNone(constraint.standard_name)
        self.assertEqual(constraint.long_name, long_name)

    def test_var_name(self):
        var_name = sentinel.var_name
        constraint = NameConstraint(var_name=var_name)
        self.assertEqual(constraint.standard_name, self.default)
        self.assertEqual(constraint.long_name, self.default)
        self.assertEqual(constraint.var_name, var_name)
        constraint = NameConstraint(None, None, var_name)
        self.assertIsNone(constraint.standard_name)
        self.assertIsNone(constraint.long_name)
        self.assertEqual(constraint.var_name, var_name)

    def test_STASH(self):
        STASH = sentinel.STASH
        constraint = NameConstraint(STASH=STASH)
        self.assertEqual(constraint.standard_name, self.default)
        self.assertEqual(constraint.long_name, self.default)
        self.assertEqual(constraint.var_name, self.default)
        self.assertEqual(constraint.STASH, STASH)
        constraint = NameConstraint(None, None, None, STASH)
        self.assertIsNone(constraint.standard_name)
        self.assertIsNone(constraint.long_name)
        self.assertIsNone(constraint.var_name)
        self.assertEqual(constraint.STASH, STASH)


class Test__cube_func(tests.IrisTest):
    def setUp(self):
        self.standard_name = sentinel.standard_name
        self.long_name = sentinel.long_name
        self.var_name = sentinel.var_name
        self.STASH = sentinel.STASH
        self.cube = Mock(standard_name=self.standard_name,
                         long_name=self.long_name,
                         var_name=self.var_name,
                         attributes=dict(STASH=self.STASH))

    def test_standard_name(self):
        # Match.
        constraint = NameConstraint(standard_name=self.standard_name)
        self.assertTrue(constraint._cube_func(self.cube))
        # Match.
        constraint = NameConstraint(self.standard_name)
        self.assertTrue(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(standard_name='wibble')
        self.assertFalse(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint('wibble')
        self.assertFalse(constraint._cube_func(self.cube))

    def test_long_name(self):
        # Match.
        constraint = NameConstraint(long_name=self.long_name)
        self.assertTrue(constraint._cube_func(self.cube))
        # Match.
        constraint = NameConstraint(self.standard_name, self.long_name)
        self.assertTrue(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(long_name=None)
        self.assertFalse(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(None, self.long_name)
        self.assertFalse(constraint._cube_func(self.cube))

    def test_var_name(self):
        # Match.
        constraint = NameConstraint(var_name=self.var_name)
        self.assertTrue(constraint._cube_func(self.cube))
        # Match.
        constraint = NameConstraint(self.standard_name, self.long_name,
                                    self.var_name)
        self.assertTrue(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(var_name=None)
        self.assertFalse(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(None, None, self.var_name)
        self.assertFalse(constraint._cube_func(self.cube))

    def test_STASH(self):
        # Match.
        constraint = NameConstraint(STASH=self.STASH)
        self.assertTrue(constraint._cube_func(self.cube))
        # Match.
        constraint = NameConstraint(self.standard_name, self.long_name,
                                    self.var_name, self.STASH)
        self.assertTrue(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(STASH=None)
        self.assertFalse(constraint._cube_func(self.cube))
        # No match.
        constraint = NameConstraint(None, None, None, self.STASH)
        self.assertFalse(constraint._cube_func(self.cube))


class Test___repr__(tests.IrisTest):
    def setUp(self):
        self.standard_name = sentinel.standard_name
        self.long_name = sentinel.long_name
        self.var_name = sentinel.var_name
        self.STASH = sentinel.STASH
        self.msg = 'NameConstraint({})'
        self.f_standard_name = 'standard_name={!r}'.format(self.standard_name)
        self.f_long_name = 'long_name={!r}'.format(self.long_name)
        self.f_var_name = 'var_name={!r}'.format(self.var_name)
        self.f_STASH = 'STASH={!r}'.format(self.STASH)

    def test(self):
        constraint = NameConstraint()
        expected = self.msg.format('')
        self.assertEqual(repr(constraint), expected)

    def test_standard_name(self):
        constraint = NameConstraint(self.standard_name)
        expected = self.msg.format(self.f_standard_name)
        self.assertEqual(repr(constraint), expected)

    def test_long_name(self):
        constraint = NameConstraint(long_name=self.long_name)
        expected = self.msg.format(self.f_long_name)
        self.assertEqual(repr(constraint), expected)
        constraint = NameConstraint(self.standard_name, self.long_name)
        args = '{}, {}'.format(self.f_standard_name, self.f_long_name)
        expected = self.msg.format(args)
        self.assertEqual(repr(constraint), expected)

    def test_var_name(self):
        constraint = NameConstraint(var_name=self.var_name)
        expected = self.msg.format(self.f_var_name)
        self.assertEqual(repr(constraint), expected)
        constraint = NameConstraint(self.standard_name, self.long_name,
                                    self.var_name)
        args = '{}, {}, {}'.format(self.f_standard_name, self.f_long_name,
                                   self.f_var_name)
        expected = self.msg.format(args)
        self.assertEqual(repr(constraint), expected)

    def test_STASH(self):
        constraint = NameConstraint(STASH=self.STASH)
        expected = self.msg.format(self.f_STASH)
        self.assertEqual(repr(constraint), expected)
        constraint = NameConstraint(self.standard_name, self.long_name,
                                    self.var_name, self.STASH)
        args = '{}, {}, {}, {}'.format(self.f_standard_name, self.f_long_name,
                                       self.f_var_name, self.f_STASH)
        expected = self.msg.format(args)
        self.assertEqual(repr(constraint), expected)


if __name__ == '__main__':
    tests.main()
