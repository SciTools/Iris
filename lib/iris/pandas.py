# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Provide conversion to and from Pandas data structures.

See also: http://pandas.pydata.org/

"""

import datetime
from itertools import chain, combinations

import cf_units
from cf_units import Unit
import cftime
import numpy as np
import numpy.ma as ma
import pandas

try:
    from pandas.core.indexes.datetimes import DatetimeIndex  # pandas >=0.20
except ImportError:
    from pandas.tseries.index import DatetimeIndex  # pandas <0.20

import iris
from iris.coords import AncillaryVariable, AuxCoord, CellMeasure, DimCoord
from iris.cube import Cube, CubeList


def _add_iris_coord(cube, name, points, dim, calendar=None):
    """
    Add a Coord to a Cube from a Pandas index or columns array.

    If no calendar is specified for a time series, Standard is assumed.

    """
    units = Unit("unknown")
    if calendar is None:
        calendar = cf_units.CALENDAR_STANDARD

    # Convert pandas datetime objects to python datetime obejcts.
    if isinstance(points, DatetimeIndex):
        points = np.array([i.to_pydatetime() for i in points])

    # Convert datetime objects to Iris' current datetime representation.
    if points.dtype == object:
        dt_types = (datetime.datetime, cftime.datetime)
        if all([isinstance(i, dt_types) for i in points]):
            units = Unit("hours since epoch", calendar=calendar)
            points = units.date2num(points)

    points = np.array(points)
    if np.issubdtype(points.dtype, np.number) and iris.util.monotonic(
        points, strict=True
    ):
        coord = DimCoord(points, units=units)
        coord.rename(name)
        cube.add_dim_coord(coord, dim)
    else:
        coord = AuxCoord(points, units=units)
        coord.rename(name)
        cube.add_aux_coord(coord, dim)


def _series_index_mapping(column: pandas.Series):
    """
    Determine which index levels of a :class:`pandas.Series` 'map' to its values.

    Achieved by checking if each index value corresponds to a single
    :class:`~pandas.Series` value.
    """
    # list(chain(*[combinations(levels_range, l + 1) for l in levels_range[:-1]]))
    if column.nunique() == 1:
        result = ()
    else:
        levels_range = range(column.index.nlevels)
        levels_combinations = chain(
            *[
                combinations(levels_range, levels + 1)
                for levels in levels_range[:-1]
            ]
        )
        for lc in levels_combinations:
            if column.groupby(level=lc).nunique().max() == 1:
                # Escape as early as possible - heavy operation.
                result = lc
                break
            result = tuple(levels_range)
    return result


def as_cube(
    pandas_array,
    copy=True,
    calendars=None,
    dim_coord_cols=None,
    aux_coord_cols=None,
    cell_measure_cols=None,
    ancillary_variable_cols=None,
):
    """
    Convert a Pandas array into an Iris cube.

    Args:

        * pandas_array - A Pandas Series or DataFrame.

    Kwargs:

        * copy      - Whether to make a copy of the data.
                      Defaults to True.

        * calendars - A dict mapping a dimension to a calendar.
                      Required to convert datetime indices/columns.

    Example usage::

        as_cube(series, calendars={0: cf_units.CALENDAR_360_DAY})
        as_cube(data_frame, calendars={1: cf_units.CALENDAR_STANDARD})

    .. note:: This function will copy your data by default.

    """
    calendars = calendars or {}
    aux_coord_cols = aux_coord_cols or []
    cell_measure_cols = cell_measure_cols or []
    ancillary_variable_cols = ancillary_variable_cols or []

    if iris.FUTURE.pandas_ndim:
        # TODO: allow for Series as well as DataFrame

        if dim_coord_cols is not None:
            try:
                pandas_array = pandas_array.set_index(dim_coord_cols)
            except Exception as e:
                message = "Unable to use dim_coord_cols as DataFrame index."
                raise ValueError(message) from e

        pandas_index = pandas_array.index
        if not pandas_index.is_unique:
            message = (
                f"DataFrame index ({pandas_index.names}) is not unique per "
                "row; cannot be used for DimCoords."
            )
            raise ValueError(message)

        pandas_array.sort_index(inplace=True)

        non_data_columns = (
            aux_coord_cols + cell_measure_cols + ancillary_variable_cols
        )
        data_columns = list(
            filter(lambda c: c not in non_data_columns, pandas_array.columns)
        )

        # Work out which dimensions each column can be mapped to.
        column_dimensions = {
            c: _series_index_mapping(pandas_array[c]) for c in non_data_columns
        }

        cube_shape = pandas_index.levshape

        class_arg_mapping = [
            (AuxCoord, aux_coord_cols, "aux_coords_and_dims"),
            (CellMeasure, cell_measure_cols, "cell_measures_and_dims"),
            (
                AncillaryVariable,
                ancillary_variable_cols,
                "ancillary_variables_and_dims",
            ),
        ]

        # TODO: check that we are getting views of the data, rather than
        #  copying lots.

        cube_kwargs = {}
        for dm_class, columns, kwarg in class_arg_mapping:
            class_kwarg = []
            for column_name in columns:
                dimensions = column_dimensions[column_name]
                content = pandas_array[column_name].to_numpy()

                # Remove duplicate entries to get down to the correct dimensions
                #  for this object. _series_index_mapping should have ensured
                #  that we are indeed removing the duplicates.
                shaped = content.reshape(cube_shape)
                indices = [0] * len(cube_shape)
                for dim in dimensions:
                    indices[dim] = slice(None)
                collapsed = shaped[tuple(indices)]

                dm_instance = dm_class(collapsed)
                # Use rename() to attempt standard_name but fall back on long_name.
                dm_instance.rename(column_name)

                class_kwarg.append((dm_instance, dimensions))

            cube_kwargs[kwarg] = class_kwarg

        # TODO: can we generalise the DimCoord section into the
        #  multi-dimensional section?
        dim_coord_kwarg = []
        for ix, dim_name in enumerate(pandas_index.names):
            dim_coord = DimCoord(pandas_index.levels[ix])
            # Use rename() to attempt standard_name but fall back on long_name.
            dim_coord.rename(dim_name)
            dim_coord_kwarg.append((dim_coord, ix))
        cube_kwargs["dim_coords_and_dims"] = dim_coord_kwarg

        cubes = CubeList()
        for column_name in data_columns:
            cube_data = (
                pandas_array[column_name].to_numpy().reshape(cube_shape)
            )
            new_cube = Cube(cube_data, **cube_kwargs)
            # Use rename() to attempt standard_name but fall back on long_name.
            new_cube.rename(column_name)
            cubes.append(new_cube)

        return cubes
    else:
        if pandas_array.ndim not in [1, 2]:
            raise ValueError(
                "Only 1D or 2D Pandas arrays "
                "can currently be conveted to Iris cubes."
            )

        # Make the copy work consistently across NumPy 1.6 and 1.7.
        # (When 1.7 takes a copy it preserves the C/Fortran ordering, but
        # 1.6 doesn't. Since we don't care about preserving the order we can
        # just force it back to C-order.)
        order = "C" if copy else "A"
        data = np.array(pandas_array, copy=copy, order=order)
        cube = Cube(np.ma.masked_invalid(data, copy=False))
        _add_iris_coord(
            cube, "index", pandas_array.index, 0, calendars.get(0, None)
        )
        if pandas_array.ndim == 2:
            _add_iris_coord(
                cube,
                "columns",
                pandas_array.columns.values,
                1,
                calendars.get(1, None),
            )
        return cube


def _as_pandas_coord(coord):
    """Convert an Iris Coord into a Pandas index or columns array."""
    index = coord.points
    if coord.units.is_time_reference():
        index = coord.units.num2date(index)
    return index


def _assert_shared(np_obj, pandas_obj):
    """Ensure the pandas object shares memory."""
    values = pandas_obj.values

    def _get_base(array):
        # Chase the stack of NumPy `base` references back to the original array
        while array.base is not None:
            array = array.base
        return array

    base = _get_base(values)
    np_base = _get_base(np_obj)
    if base is not np_base:
        msg = "Pandas {} does not share memory".format(
            type(pandas_obj).__name__
        )
        raise AssertionError(msg)


def as_series(cube, copy=True):
    """
    Convert a 1D cube to a Pandas Series.

    Args:

        * cube - The cube to convert to a Pandas Series.

    Kwargs:

        * copy - Whether to make a copy of the data.
                 Defaults to True. Must be True for masked data.

    .. note::

        This function will copy your data by default.
        If you have a large array that cannot be copied,
        make sure it is not masked and use copy=False.

    """
    data = cube.data
    if ma.isMaskedArray(data):
        if not copy:
            raise ValueError("Masked arrays must always be copied.")
        data = data.astype("f").filled(np.nan)
    elif copy:
        data = data.copy()

    index = None
    if cube.dim_coords:
        index = _as_pandas_coord(cube.dim_coords[0])

    series = pandas.Series(data, index)
    if not copy:
        _assert_shared(data, series)

    return series


def as_data_frame(cube, copy=True):
    """
    Convert a 2D cube to a Pandas DataFrame.

    Args:

        * cube - The cube to convert to a Pandas DataFrame.

    Kwargs:

        * copy - Whether to make a copy of the data.
                 Defaults to True. Must be True for masked data
                 and some data types (see notes below).

    .. note::

        This function will copy your data by default.
        If you have a large array that cannot be copied,
        make sure it is not masked and use copy=False.

    .. note::

        Pandas will sometimes make a copy of the array,
        for example when creating from an int32 array.
        Iris will detect this and raise an exception if copy=False.

    """
    data = cube.data
    if ma.isMaskedArray(data):
        if not copy:
            raise ValueError("Masked arrays must always be copied.")
        data = data.astype("f").filled(np.nan)
    elif copy:
        data = data.copy()

    index = columns = None
    if cube.coords(dimensions=[0]):
        index = _as_pandas_coord(cube.coord(dimensions=[0]))
    if cube.coords(dimensions=[1]):
        columns = _as_pandas_coord(cube.coord(dimensions=[1]))

    data_frame = pandas.DataFrame(data, index, columns)
    if not copy:
        _assert_shared(data, data_frame)

    return data_frame
