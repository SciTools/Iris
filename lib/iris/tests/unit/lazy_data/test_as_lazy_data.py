# (C) British Crown Copyright 2017 - 2019, Met Office
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
"""Test the function :func:`iris._lazy data.as_lazy_data`."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import dask.array as da
import dask.config
import numpy as np
import numpy.ma as ma

from iris._lazy_data import as_lazy_data, _optimum_chunksize
from iris.tests import mock


class Test_as_lazy_data(tests.IrisTest):
    def test_lazy(self):
        data = da.from_array(np.arange(24).reshape((2, 3, 4)), chunks='auto')
        result = as_lazy_data(data)
        self.assertIsInstance(result, da.core.Array)

    def test_real(self):
        data = np.arange(24).reshape((2, 3, 4))
        result = as_lazy_data(data)
        self.assertIsInstance(result, da.core.Array)

    def test_masked(self):
        data = np.ma.masked_greater(np.arange(24), 10)
        result = as_lazy_data(data)
        self.assertIsInstance(result, da.core.Array)

    def test_non_default_chunks(self):
        data = np.arange(24)
        chunks = (12,)
        lazy_data = as_lazy_data(data, chunks=chunks)
        result, = np.unique(lazy_data.chunks)
        self.assertEqual(result, 24)

    def test_with_masked_constant(self):
        masked_data = ma.masked_array([8], mask=True)
        masked_constant = masked_data[0]
        result = as_lazy_data(masked_constant)
        self.assertIsInstance(result, da.core.Array)


class Test__optimised_chunks(tests.IrisTest):
    # Stable, known chunksize for testing.
    FIXED_CHUNKSIZE_LIMIT = 1024 * 1024 * 64

    @staticmethod
    def _dummydata(shape):
        return mock.Mock(spec=da.core.Array,
                         dtype=np.dtype('f4'),
                         shape=shape)

    def test_chunk_size_limiting(self):
        # Check default chunksizes for large data (with a known size limit).
        given_shapes_and_resulting_chunks = [
            ((16, 1024, 1024), (16, 1024, 1024)),  # largest unmodified
            ((17, 1011, 1022), (8, 1011, 1022)),
            ((16, 1024, 1025), (8, 1024, 1025)),
            ((1, 17, 1011, 1022), (1, 8, 1011, 1022)),
            ((17, 1, 1011, 1022), (8, 1, 1011, 1022)),
            ((11, 2, 1011, 1022), (5, 2, 1011, 1022))
        ]
        err_fmt = 'Result of optimising chunks {} was {}, expected {}'
        for (shape, expected) in given_shapes_and_resulting_chunks:
            chunks = _optimum_chunksize(shape, shape,
                                        limit=self.FIXED_CHUNKSIZE_LIMIT)
            msg = err_fmt.format(shape, chunks, expected)
            self.assertEqual(chunks, expected, msg)

    def test_chunk_size_expanding(self):
        # Check the expansion of small chunks, (with a known size limit).
        given_shapes_and_resulting_chunks = [
            ((1, 100, 100), (16, 100, 100), (16, 100, 100)),
            ((1, 100, 100), (5000, 100, 100), (1677, 100, 100)),
            ((3, 300, 200), (10000, 3000, 2000), (3, 2700, 2000)),
            ((3, 300, 200), (10000, 300, 2000), (27, 300, 2000)),
            ((3, 300, 200), (8, 300, 2000), (8, 300, 2000)),
        ]
        err_fmt = 'Result of optimising shape={};chunks={} was {}, expected {}'
        for (shape, fullshape, expected) in given_shapes_and_resulting_chunks:
            chunks = _optimum_chunksize(chunks=shape, shape=fullshape,
                                        limit=self.FIXED_CHUNKSIZE_LIMIT)
            msg = err_fmt.format(fullshape, shape, chunks, expected)
            self.assertEqual(chunks, expected, msg)

    def test_default_chunksize(self):
        # Check that the "ideal" chunksize is taken from the dask config.
        with dask.config.set({'array.chunk-size': '20b'}):
            chunks = _optimum_chunksize((1, 8),
                                        shape=(400, 20),
                                        dtype=np.dtype('f4'))
            self.assertEqual(chunks, (1, 4))

    def test_default_chunks_limiting(self):
        # Check that chunking is still controlled when no specific 'chunks'
        # is passed.
        limitcall_patch = self.patch('iris._lazy_data._optimum_chunksize')
        test_shape = (3, 2, 4)
        data = self._dummydata(test_shape)
        as_lazy_data(data)
        self.assertEqual(limitcall_patch.call_args_list,
                         [mock.call(list(test_shape),
                                    shape=test_shape,
                                    dtype=np.dtype('f4'))])

    def test_large_specific_chunk_passthrough(self):
        # Check that even a too-large specific 'chunks' arg is honoured.
        limitcall_patch = self.patch('iris._lazy_data._optimum_chunksize')
        huge_test_shape = (1001, 1002, 1003, 1004)
        data = self._dummydata(huge_test_shape)
        result = as_lazy_data(data, chunks=huge_test_shape)
        self.assertEqual(limitcall_patch.call_args_list,
                         [mock.call(huge_test_shape,
                                    shape=huge_test_shape,
                                    dtype=np.dtype('f4'))])
        self.assertEqual(result.shape, huge_test_shape)


if __name__ == '__main__':
    tests.main()
