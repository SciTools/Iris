# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for equality testing of different constraint types."""

from __future__ import absolute_import, division, print_function
from six.moves import filter, input, map, range, zip  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris._constraints import Constraint, AttributeConstraint, NameConstraint


class Test_Constraint__hash__(tests.IrisTest):
    def test_empty(self):
        c1 = Constraint()
        c2 = Constraint()
        self.assertEqual(hash(c1), hash(c1))
        self.assertNotEqual(hash(c1), hash(c2))


class Test_Constraint__eq__(tests.IrisTest):
    def test_empty_same(self):
        c1 = Constraint()
        c2 = Constraint()
        self.assertEqual(c1, c2)
        self.assertIsNot(c1, c2)

    def test_emptyname_same(self):
        c1 = Constraint("")
        c2 = Constraint("")
        self.assertEqual(c1, c2)

    def test_empty_emptyname_differ(self):
        c1 = Constraint()
        c2 = Constraint("")
        self.assertNotEqual(c1, c2)

    def test_names_same(self):
        c1 = Constraint("a")
        c2 = Constraint("a")
        self.assertEqual(c1, c2)

    def test_names_differ(self):
        c1 = Constraint("a")
        c2 = Constraint("b")
        self.assertNotEqual(c1, c2)

    def test_funcs_same(self):
        # *Same* functions match
        def func(cube):
            return False

        c1 = Constraint(cube_func=func)
        c2 = Constraint(cube_func=func)
        self.assertEqual(c1, c2)

    def test_funcs_differ(self):
        # Identical but different funcs do not match.
        c1 = Constraint(cube_func=lambda c: False)
        c2 = Constraint(cube_func=lambda c: False)
        self.assertNotEqual(c1, c2)

    def test_coord_names_same(self):
        c1 = Constraint(coord=3)
        c2 = Constraint(coord=3)
        self.assertEqual(c1, c2)

    def test_coord_names_differ(self):
        c1 = Constraint(coord=3)
        c2 = Constraint(coord2=3)
        self.assertNotEqual(c1, c2)

    def test_coord_values_differ(self):
        c1 = Constraint(coord=3)
        c2 = Constraint(coord=4)
        self.assertNotEqual(c1, c2)

    def test_coord_orders_differ(self):
        # We *could* maybe ignore Coordinate order, but at present we don't.
        c1 = Constraint(a=1, b=2)
        c2 = Constraint(b=2, a=1)
        self.assertNotEqual(c1, c2)

    def test_coord_values_functions_same(self):
        def func(coord):
            return False

        c1 = Constraint(coord=func)
        c2 = Constraint(coord=func)
        self.assertEqual(c1, c2)

    def test_coord_values_functions_differ(self):
        # Identical functions are not the same.
        c1 = Constraint(coord=lambda c: True)
        c2 = Constraint(coord=lambda c: True)
        self.assertNotEqual(c1, c2)

    def test_coord_values_and_keys_same(self):
        # **kwargs and 'coord_values=' are combined without distinction.
        c1 = Constraint(coord_values={"a": [2, 3]})
        c2 = Constraint(a=[2, 3])
        self.assertEqual(c1, c2)


class Test_AttributeConstraint__hash__(tests.IrisTest):
    def test_empty(self):
        c1 = AttributeConstraint()
        c2 = AttributeConstraint()
        self.assertEqual(hash(c1), hash(c1))
        self.assertNotEqual(hash(c1), hash(c2))


class Test_AttributeConstraint__eq__(tests.IrisTest):
    def test_empty_same(self):
        c1 = AttributeConstraint()
        c2 = AttributeConstraint()
        self.assertEqual(c1, c2)
        self.assertIsNot(c1, c2)

    def test_attribute_plain_empty_diff(self):
        c1 = AttributeConstraint()
        c2 = Constraint()
        self.assertNotEqual(c1, c2)

    def test_names_same(self):
        c1 = AttributeConstraint(a=1)
        c2 = AttributeConstraint(a=1)
        self.assertEqual(c1, c2)

    def test_names_diff(self):
        c1 = AttributeConstraint(a=1)
        c2 = AttributeConstraint(a=1, b=1)
        self.assertNotEqual(c1, c2)

    def test_values_diff(self):
        c1 = AttributeConstraint(a=1, b=1)
        c2 = AttributeConstraint(a=1, b=2)
        self.assertNotEqual(c1, c2)

    def test_func_same(self):
        def func(attrs):
            return False

        c1 = AttributeConstraint(a=func)
        c2 = AttributeConstraint(a=func)
        self.assertEqual(c1, c2)

    def test_func_diff(self):
        c1 = AttributeConstraint(a=lambda a: False)
        c2 = AttributeConstraint(a=lambda a: False)
        self.assertNotEqual(c1, c2)


class Test_NameConstraint__hash__(tests.IrisTest):
    def test_empty(self):
        c1 = NameConstraint()
        c2 = NameConstraint()
        self.assertEqual(hash(c1), hash(c1))
        self.assertNotEqual(hash(c1), hash(c2))


class Test_NameConstraint__eq__(tests.IrisTest):
    def test_empty_same(self):
        c1 = NameConstraint()
        c2 = NameConstraint()
        self.assertEqual(c1, c2)
        self.assertIsNot(c1, c2)

    def test_attribute_plain_empty_diff(self):
        c1 = NameConstraint()
        c2 = Constraint()
        self.assertNotEqual(c1, c2)

    def test_names_same(self):
        c1 = NameConstraint(standard_name="air_temperature")
        c2 = NameConstraint(standard_name="air_temperature")
        self.assertEqual(c1, c2)

    def test_full_same(self):
        c1 = NameConstraint(
            standard_name="air_temperature",
            long_name="temp",
            var_name="tair",
            STASH="m01s02i003",
        )
        c2 = NameConstraint(
            standard_name="air_temperature",
            long_name="temp",
            var_name="tair",
            STASH="m01s02i003",
        )
        self.assertEqual(c1, c2)

    def test_missing_diff(self):
        c1 = NameConstraint(standard_name="air_temperature", var_name="tair")
        c2 = NameConstraint(standard_name="air_temperature")
        self.assertNotEqual(c1, c2)

    def test_standard_name_diff(self):
        c1 = NameConstraint(standard_name="air_temperature")
        c2 = NameConstraint(standard_name="height")
        self.assertNotEqual(c1, c2)

    def test_long_name_diff(self):
        c1 = NameConstraint(long_name="temp")
        c2 = NameConstraint(long_name="t3")
        self.assertNotEqual(c1, c2)

    def test_var_name_diff(self):
        c1 = NameConstraint(var_name="tair")
        c2 = NameConstraint(var_name="xxx")
        self.assertNotEqual(c1, c2)

    def test_stash_diff(self):
        c1 = NameConstraint(STASH="m01s02i003")
        c2 = NameConstraint(STASH="m01s02i777")
        self.assertNotEqual(c1, c2)

    def test_func_same(self):
        def func(name):
            return True

        c1 = NameConstraint(STASH="m01s02i003", long_name=func)
        c2 = NameConstraint(STASH="m01s02i003", long_name=func)
        self.assertEqual(c1, c2)

    def test_func_diff(self):
        c1 = NameConstraint(STASH="m01s02i003", long_name=lambda n: True)
        c2 = NameConstraint(STASH="m01s02i003", long_name=lambda n: True)
        self.assertNotEqual(c1, c2)


class Test___hash__(tests.IrisTest):
    def test_empty(self):
        c1 = Constraint() & Constraint()
        c2 = Constraint() & Constraint()
        self.assertEqual(hash(c1), hash(c1))
        self.assertNotEqual(hash(c1), hash(c2))


class Test_ConstraintCombination__eq__(tests.IrisTest):
    def test_empty_same(self):
        c1 = Constraint() & Constraint()
        c2 = Constraint() & Constraint()
        self.assertEqual(c1, c2)
        self.assertIsNot(c1, c2)

    def test_multi_components_same(self):
        c1 = Constraint("a") & Constraint(b=1)
        c2 = Constraint("a") & Constraint(b=1)
        self.assertEqual(c1, c2)

    def test_multi_components_diff(self):
        c1 = Constraint("a") & Constraint(b=1, c=2)
        c2 = Constraint("a") & Constraint(b=1)
        self.assertNotEqual(c1, c2)


if __name__ == "__main__":
    tests.main()
