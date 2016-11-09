# (C) British Crown Copyright 2016, Met Office
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
Support for fast matrix loading of structured UM files.

This works with either PP or Fieldsfiles.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six

from contextlib import contextmanager
import threading

import iris
from iris.cube import CubeList


def _basic_load_function(filename, pp_filter=None, **kwargs):
    # The low-level 'fields from filename' loader.
    # Referred to in generic rules processing as the 'generator' function.
    #
    # Called by generic rules code.
    # replaces pp.load (and the like)
    #
    # It yields a sequence of "fields".
    #
    # In this case our 'fields' are :
    # iris.fileformats.um._fast_load_structured_fields.FieldCollation
    #
    # Also in our case, we need to apply the basic single-field filtering
    # operation that speeds up phenomenon selection.
    # Therefore, the actual loader will pass us this as a keyword, if it is
    # needed.
    # The remaining keywords are 'passed on' to the lower-level function.
    #
    # NOTE: so, this is what is passed as the 'field' to user callbacks.
    from iris.experimental.fieldsfile import _structured_loader
    from iris.fileformats.um._fast_load_structured_fields import \
        group_structured_fields
    loader = _structured_loader(filename)
    fields = iter(field
                  for field in loader(filename, **kwargs)
                  if pp_filter is None or pp_filter(field))
    return group_structured_fields(fields)


def _convert(collation):
    # The call recorded in the 'loader' structure of the the generic rules
    # code (iris.fileformats.rules), that converts a 'field' into a 'raw cube'.
    from iris.experimental.fieldsfile import _convert_collation
    return _convert_collation(collation)


def _combine_structured_cubes(cubes):
    # Combine structured cubes from different sourcefiles, in the style of
    # merge/concatenate.
    #
    # Because standard Cube.merge employed in loading can't do this.
    if STRUCTURED_LOAD_CONTROLS.structured_load_is_raw:
        # Cross-file concatenate is disabled, during a "load_raw" call.
        result = cubes
    else:
        result = iter(CubeList(cubes).concatenate())
    return result


class StructuredLoadFlags(threading.local):
    # A thread-safe object to control structured loading operations.
    # The object properties are the control flags.
    #
    # Inheriting from 'threading.local' provides a *separate* set of the
    # object properties for each thread.
    def __init__(self):
        # Control whether iris load functions do structured loads.
        self.loads_use_structured = False
        # Control whether structured load 'combine' is enabled.
        self.structured_load_is_raw = False

    @contextmanager
    def context(self,
                loads_use_structured=None,
                structured_load_is_raw=None):
        # Snapshot current states, for restoration afterwards.
        old_structured = self.loads_use_structured
        old_raw_load = self.structured_load_is_raw
        try:
            # Set flags for duration, as requested.
            if loads_use_structured is not None:
                self.loads_use_structured = loads_use_structured
            if structured_load_is_raw is not None:
                self.structured_load_is_raw = structured_load_is_raw
            # Yield to caller operation.
            yield
        finally:
            # Restore entry state of flags.
            self.loads_use_structured = old_structured
            self.structured_load_is_raw = old_raw_load


# A singleton structured-load-control object.
# Used in :meth:`iris.fileformats.pp._load_cubes_variable_loader`.
STRUCTURED_LOAD_CONTROLS = StructuredLoadFlags()


@contextmanager
def structured_um_loading():
    """
    Load cubes from structured UM Fieldsfile and PP files.

    This is a context manager that enables an alternative loading mechanism for
    'structured' UM files, providing much faster load times.
    Within the scope of the context manager, this affects all standard Iris
    load functions (:func:`~iris.load`, :func:`~iris.load_cube`,
    :func:`~iris.load_cubes` and :func:`~iris.load_raw`), when loading from UM
    format files (PP or fieldsfiles).

    For example:

        >>> import iris
        >>> filepath = iris.sample_data_path('uk_hires.pp')
        >>> from iris.fileformats.um import structured_um_loading
        >>> with structured_um_loading():
        ...     cube = iris.load_cube(filepath, 'air_potential_temperature')
        ...
        >>> cube
        <iris 'Cube' of air_potential_temperature / (K) \
(time: 3; model_level_number: 7; grid_latitude: 204; grid_longitude: 187)>

    Notes on applicability:

    This is a streamlined load operation, to be used *only* on fieldsfiles or
    PP files whose fields repeat regularly over the same vertical levels
    and times.

    The results aim to be equivalent to those generated by :func:`iris.load`,
    but the operation is substantially faster for input that is structured.

    The structured input files must conform to the following requirements:

    *  the file must contain fields for all possible combinations of the
       vertical levels and time points found in the file.

    *  the fields must occur in a regular repeating order within the file.

       (For example: a sequence of fields for NV vertical levels, repeated
       for NP different forecast periods, repeated for NT different
       forecast times).

    *  all other metadata must be identical across all fields of the same
       phenomenon.

    Each group of fields with the same values of LBUSER4, LBUSER7 and
    LBPROC is identified as a separate phenomenon:  These groups are
    processed independently and returned as separate result cubes.

    .. note::

        The resulting time-related coordinates ('time', 'forecast_time' and
        'forecast_period') may be mapped to shared cube dimensions and in some
        cases can also be multidimensional.  However, the vertical level
        information *must* have a simple one-dimensional structure, independent
        of the time points, otherwise an error will be raised.

    .. note::

        Where input data does *not* have a fully regular arrangement, the
        corresponding result cube will have a single anonymous extra dimension
        which indexes over all the input fields.

        This can happen if, for example, some fields are missing; or have
        slightly different metadata; or appear out of order in the file.

    .. warning::

        Any non-regular metadata variation in the input should be strictly
        avoided, as not all irregularities are detected, which can cause
        erroneous results.

    """
    with STRUCTURED_LOAD_CONTROLS.context(loads_use_structured=True):
        yield


@contextmanager
def _raw_structured_loading():
    """
    Private context manager called by :func:`iris.load_raw` to prevent
    structured loading from concatenating its result cubes in that case.

    """
    with STRUCTURED_LOAD_CONTROLS.context(structured_load_is_raw=True):
        yield
