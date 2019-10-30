# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for :func:`iris.fileformats.rules._make_cube`."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import six
from unittest import mock
import warnings

import numpy as np

from iris.fileformats.rules import _make_cube
from iris.fileformats.rules import ConversionMetadata


class Test(tests.IrisTest):
    def test_invalid_units(self):
        # Mock converter() function that returns an invalid
        # units string amongst the collection of other elements.
        factories = None
        references = None
        standard_name = None
        long_name = None
        units = 'wibble'  # Invalid unit.
        attributes = dict(source='test')
        cell_methods = None
        dim_coords_and_dims = None
        aux_coords_and_dims = None
        metadata = ConversionMetadata(factories, references,
                                      standard_name, long_name, units,
                                      attributes, cell_methods,
                                      dim_coords_and_dims, aux_coords_and_dims)
        converter = mock.Mock(return_value=metadata)

        data = np.arange(3.)
        field = mock.Mock(core_data=lambda: data,
                          bmdi=9999.,
                          realised_dtype=data.dtype)
        with warnings.catch_warnings(record=True) as warn:
            warnings.simplefilter("always")
            cube, factories, references = _make_cube(field, converter)

        # Check attributes dictionary is correctly populated.
        expected_attributes = attributes.copy()
        expected_attributes['invalid_units'] = units
        self.assertEqual(cube.attributes, expected_attributes)

        # Check warning was raised.
        self.assertEqual(len(warn), 1)
        exp_emsg = 'invalid units {!r}'.format(units)
        six.assertRegex(self, str(warn[0]), exp_emsg)


if __name__ == "__main__":
    tests.main()
