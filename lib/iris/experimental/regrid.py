# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Regridding functions.

"""

import copy
import functools
import warnings

import cartopy.crs as ccrs
import cf_units
import numpy as np
import numpy.ma as ma
import scipy.interpolate

import iris.analysis.cartography
from iris.analysis._interpolation import (
    get_xy_dim_coords,
    get_xy_coords,
    snapshot_grid,
)
from iris.analysis._regrid import (
    RectilinearRegridder,
    _regrid_weighted_curvilinear_to_rectilinear__prepare,
    _regrid_weighted_curvilinear_to_rectilinear__perform,
)
import iris.coord_systems
import iris.cube
from iris.util import _meshgrid


def _get_xy_coords(cube):
    """
    Return the x and y coordinates from a cube.

    This function will preferentially return a pair of dimension
    coordinates (if there are more than one potential x or y dimension
    coordinates a ValueError will be raised). If the cube does not have
    a pair of x and y dimension coordinates it will return 1D auxiliary
    coordinates (including scalars). If there is not one and only one set
    of x and y auxiliary coordinates a ValueError will be raised.

    Having identified the x and y coordinates, the function checks that they
    have equal coordinate systems and that they do not occupy the same
    dimension on the cube.

    Args:

    * cube:
        An instance of :class:`iris.cube.Cube`.

    Returns:
        A tuple containing the cube's x and y coordinates.

    """
    # Look for a suitable dimension coords first.
    x_coords = cube.coords(axis="x", dim_coords=True)
    if not x_coords:
        # If there is no x coord in dim_coords look for scalars or
        # monotonic coords in aux_coords.
        x_coords = [
            coord
            for coord in cube.coords(axis="x", dim_coords=False)
            if coord.ndim == 1 and coord.is_monotonic()
        ]
    if len(x_coords) != 1:
        raise ValueError(
            "Cube {!r} must contain a single 1D x "
            "coordinate.".format(cube.name())
        )
    x_coord = x_coords[0]

    # Look for a suitable dimension coords first.
    y_coords = cube.coords(axis="y", dim_coords=True)
    if not y_coords:
        # If there is no y coord in dim_coords look for scalars or
        # monotonic coords in aux_coords.
        y_coords = [
            coord
            for coord in cube.coords(axis="y", dim_coords=False)
            if coord.ndim == 1 and coord.is_monotonic()
        ]
    if len(y_coords) != 1:
        raise ValueError(
            "Cube {!r} must contain a single 1D y "
            "coordinate.".format(cube.name())
        )
    y_coord = y_coords[0]

    if x_coord.coord_system != y_coord.coord_system:
        raise ValueError(
            "The cube's x ({!r}) and y ({!r}) "
            "coordinates must have the same coordinate "
            "system.".format(x_coord.name(), y_coord.name())
        )

    # The x and y coordinates must describe different dimensions
    # or be scalar coords.
    x_dims = cube.coord_dims(x_coord)
    x_dim = None
    if x_dims:
        x_dim = x_dims[0]

    y_dims = cube.coord_dims(y_coord)
    y_dim = None
    if y_dims:
        y_dim = y_dims[0]

    if x_dim is not None and y_dim == x_dim:
        raise ValueError(
            "The cube's x and y coords must not describe the "
            "same data dimension."
        )

    return x_coord, y_coord


def _within_bounds(src_bounds, tgt_bounds, orderswap=False):
    """
    Determine which target bounds lie within the extremes of the source bounds.

    Args:

    * src_bounds (ndarray):
        An (n, 2) shaped array of monotonic contiguous source bounds.
    * tgt_bounds (ndarray):
        An (n, 2) shaped array corresponding to the target bounds.

    Kwargs:

    * orderswap (bool):
        A Boolean indicating whether the target bounds are in descending order
        (True). Defaults to False.

    Returns:
        Boolean ndarray, indicating whether each target bound is within the
        extremes of the source bounds.

    """
    min_bound = np.min(src_bounds) - 1e-14
    max_bound = np.max(src_bounds) + 1e-14

    # Swap upper-lower is necessary.
    if orderswap is True:
        upper, lower = tgt_bounds.T
    else:
        lower, upper = tgt_bounds.T

    return ((lower <= max_bound) * (lower >= min_bound)) * (
        (upper <= max_bound) * (upper >= min_bound)
    )


def _cropped_bounds(bounds, lower, upper):
    """
    Return a new bounds array and corresponding slice object (or indices) of
    the original data array, resulting from cropping the provided bounds
    between the specified lower and upper values. The bounds at the
    extremities will be truncated so that they start and end with lower and
    upper.

    This function will return an empty NumPy array and slice if there is no
    overlap between the region covered by bounds and the region from lower to
    upper.

    If lower > upper the resulting bounds may not be contiguous and the
    indices object will be a tuple of indices rather than a slice object.

    Args:

    * bounds:
        An (n, 2) shaped array of monotonic contiguous bounds.
    * lower:
        Lower bound at which to crop the bounds array.
    * upper:
        Upper bound at which to crop the bounds array.

    Returns:
        A tuple of the new bounds array and the corresponding slice object or
        indices from the zeroth axis of the original array.

    """
    reversed_flag = False
    # Ensure order is increasing.
    if bounds[0, 0] > bounds[-1, 0]:
        # Reverse bounds
        bounds = bounds[::-1, ::-1]
        reversed_flag = True

    # Number of bounds.
    n = bounds.shape[0]

    if lower <= upper:
        if lower > bounds[-1, 1] or upper < bounds[0, 0]:
            new_bounds = bounds[0:0]
            indices = slice(0, 0)
        else:
            # A single region lower->upper.
            if lower < bounds[0, 0]:
                # Region extends below bounds so use first lower bound.
                lindex = 0
                lower = bounds[0, 0]
            else:
                # Index of last lower bound less than or equal to lower.
                lindex = np.nonzero(bounds[:, 0] <= lower)[0][-1]
            if upper > bounds[-1, 1]:
                # Region extends above bounds so use last upper bound.
                uindex = n - 1
                upper = bounds[-1, 1]
            else:
                # Index of first upper bound greater than or equal to
                # upper.
                uindex = np.nonzero(bounds[:, 1] >= upper)[0][0]
            # Extract the bounds in our region defined by lower->upper.
            new_bounds = np.copy(bounds[lindex : (uindex + 1), :])
            # Replace first and last values with specified bounds.
            new_bounds[0, 0] = lower
            new_bounds[-1, 1] = upper
            if reversed_flag:
                indices = slice(n - (uindex + 1), n - lindex)
            else:
                indices = slice(lindex, uindex + 1)
    else:
        # Two regions [0]->upper, lower->[-1]
        # [0]->upper
        if upper < bounds[0, 0]:
            # Region outside src bounds.
            new_bounds_left = bounds[0:0]
            indices_left = tuple()
            slice_left = slice(0, 0)
        else:
            if upper > bounds[-1, 1]:
                # Whole of bounds.
                uindex = n - 1
                upper = bounds[-1, 1]
            else:
                # Index of first upper bound greater than or equal to upper.
                uindex = np.nonzero(bounds[:, 1] >= upper)[0][0]
            # Extract the bounds in our region defined by [0]->upper.
            new_bounds_left = np.copy(bounds[0 : (uindex + 1), :])
            # Replace last value with specified bound.
            new_bounds_left[-1, 1] = upper
            if reversed_flag:
                indices_left = tuple(range(n - (uindex + 1), n))
                slice_left = slice(n - (uindex + 1), n)
            else:
                indices_left = tuple(range(0, uindex + 1))
                slice_left = slice(0, uindex + 1)
        # lower->[-1]
        if lower > bounds[-1, 1]:
            # Region is outside src bounds.
            new_bounds_right = bounds[0:0]
            indices_right = tuple()
            slice_right = slice(0, 0)
        else:
            if lower < bounds[0, 0]:
                # Whole of bounds.
                lindex = 0
                lower = bounds[0, 0]
            else:
                # Index of last lower bound less than or equal to lower.
                lindex = np.nonzero(bounds[:, 0] <= lower)[0][-1]
            # Extract the bounds in our region defined by lower->[-1].
            new_bounds_right = np.copy(bounds[lindex:, :])
            # Replace first value with specified bound.
            new_bounds_right[0, 0] = lower
            if reversed_flag:
                indices_right = tuple(range(0, n - lindex))
                slice_right = slice(0, n - lindex)
            else:
                indices_right = tuple(range(lindex, n))
                slice_right = slice(lindex, None)

        if reversed_flag:
            # Flip everything around.
            indices_left, indices_right = indices_right, indices_left
            slice_left, slice_right = slice_right, slice_left

        # Combine regions.
        new_bounds = np.concatenate((new_bounds_left, new_bounds_right))
        # Use slices if possible, but if we have two regions use indices.
        if indices_left and indices_right:
            indices = indices_left + indices_right
        elif indices_left:
            indices = slice_left
        elif indices_right:
            indices = slice_right
        else:
            indices = slice(0, 0)

    if reversed_flag:
        new_bounds = new_bounds[::-1, ::-1]

    return new_bounds, indices


def _cartesian_area(y_bounds, x_bounds):
    """
    Return an array of the areas of each cell given two arrays
    of cartesian bounds.

    Args:

    * y_bounds:
        An (n, 2) shaped NumPy array.
    * x_bounds:
        An (m, 2) shaped NumPy array.

    Returns:
        An (n, m) shaped Numpy array of areas.

    """
    heights = y_bounds[:, 1] - y_bounds[:, 0]
    widths = x_bounds[:, 1] - x_bounds[:, 0]
    return np.abs(np.outer(heights, widths))


def _spherical_area(y_bounds, x_bounds, radius=1.0):
    """
    Return an array of the areas of each cell on a sphere
    given two arrays of latitude and longitude bounds in radians.

    Args:

    * y_bounds:
        An (n, 2) shaped NumPy array of latitide bounds in radians.
    * x_bounds:
        An (m, 2) shaped NumPy array of longitude bounds in radians.
    * radius:
        Radius of the sphere. Default is 1.0.

    Returns:
        An (n, m) shaped Numpy array of areas.

    """
    return iris.analysis.cartography._quadrant_area(y_bounds, x_bounds, radius)


def _get_bounds_in_units(coord, units, dtype):
    """Return a copy of coord's bounds in the specified units and dtype."""
    # The bounds are cast to dtype before conversion to prevent issues when
    # mixing float32 and float64 types.
    return coord.units.convert(coord.bounds.astype(dtype), units).astype(dtype)


def _weighted_mean_with_mdtol(data, weights, axis=None, mdtol=0):
    """
    Return the weighted mean of an array over the specified axis
    using the provided weights (if any) and a permitted fraction of
    masked data.

    Args:

    * data (array-like):
        Data to be averaged.

    * weights (array-like):
        An array of the same shape as the data that specifies the contribution
        of each corresponding data element to the calculated mean.

    Kwargs:

    * axis (int or tuple of ints):
        Axis along which the mean is computed. The default is to compute
        the mean of the flattened array.

    * mdtol (float):
        Tolerance of missing data. The value returned in each element of the
        returned array will be masked if the fraction of masked data exceeds
        mdtol. This fraction is weighted by the `weights` array if one is
        provided. mdtol=0 means no missing data is tolerated
        while mdtol=1 will mean the resulting element will be masked if and
        only if all the contributing elements of data are masked.
        Defaults to 0.

    Returns:
        Numpy array (possibly masked) or scalar.

    """
    if ma.is_masked(data):
        res, unmasked_weights_sum = ma.average(
            data, weights=weights, axis=axis, returned=True
        )
        if mdtol < 1:
            weights_sum = weights.sum(axis=axis)
            frac_masked = 1 - np.true_divide(unmasked_weights_sum, weights_sum)
            mask_pt = frac_masked > mdtol
            if np.any(mask_pt) and not isinstance(res, ma.core.MaskedConstant):
                if np.isscalar(res):
                    res = ma.masked
                elif ma.isMaskedArray(res):
                    res.mask |= mask_pt
                else:
                    res = ma.masked_array(res, mask=mask_pt)
    else:
        res = np.average(data, weights=weights, axis=axis)
    return res


def _regrid_area_weighted_array(
    src_data,
    x_dim,
    y_dim,
    src_x_bounds,
    src_y_bounds,
    grid_x_bounds,
    grid_y_bounds,
    grid_x_decreasing,
    grid_y_decreasing,
    area_func,
    circular=False,
    mdtol=0,
):
    """
    Regrid the given data from its source grid to a new grid using
    an area weighted mean to determine the resulting data values.

    .. note::

        Elements in the returned array that lie either partially
        or entirely outside of the extent of the source grid will
        be masked irrespective of the value of mdtol.

    Args:

    * src_data:
        An N-dimensional NumPy array.
    * x_dim:
        The X dimension within `src_data`.
    * y_dim:
        The Y dimension within `src_data`.
    * src_x_bounds:
        A NumPy array of bounds along the X axis defining the source grid.
    * src_y_bounds:
        A NumPy array of bounds along the Y axis defining the source grid.
    * grid_x_bounds:
        A NumPy array of bounds along the X axis defining the new grid.
    * grid_y_bounds:
        A NumPy array of bounds along the Y axis defining the new grid.
    * grid_x_decreasing:
        Boolean indicating whether the X coordinate of the new grid is
        in descending order.
    * grid_y_decreasing:
        Boolean indicating whether the Y coordinate of the new grid is
        in descending order.
    * area_func:
        A function that returns an (p, q) array of weights given an (p, 2)
        shaped array of Y bounds and an (q, 2) shaped array of X bounds.

    Kwargs:

    * circular:
        A boolean indicating whether the `src_x_bounds` are periodic. Default
        is False.

    * mdtol:
        Tolerance of missing data. The value returned in each element of the
        returned array will be masked if the fraction of missing data exceeds
        mdtol. This fraction is calculated based on the area of masked cells
        within each target cell. mdtol=0 means no missing data is tolerated
        while mdtol=1 will mean the resulting element will be masked if and
        only if all the overlapping elements of the source grid are masked.
        Defaults to 0.

    Returns:
        The regridded data as an N-dimensional NumPy array. The lengths
        of the X and Y dimensions will now match those of the target
        grid.

    """

    def _calculate_regrid_area_weighted_weights(
        src_x_bounds,
        src_y_bounds,
        grid_x_bounds,
        grid_y_bounds,
        grid_x_decreasing,
        grid_y_decreasing,
        area_func,
        circular=False,
    ):
        """
        Compute the area weights used for area-weighted regridding.

        """
        # Determine which grid bounds are within src extent.
        y_within_bounds = _within_bounds(
            src_y_bounds, grid_y_bounds, grid_y_decreasing
        )
        x_within_bounds = _within_bounds(
            src_x_bounds, grid_x_bounds, grid_x_decreasing
        )

        # Cache which src_bounds are within grid bounds
        cached_x_bounds = []
        cached_x_indices = []
        max_x_indices = 0
        for (x_0, x_1) in grid_x_bounds:
            if grid_x_decreasing:
                x_0, x_1 = x_1, x_0
            x_bounds, x_indices = _cropped_bounds(src_x_bounds, x_0, x_1)
            cached_x_bounds.append(x_bounds)
            cached_x_indices.append(x_indices)
            # Keep record of the largest slice
            if isinstance(x_indices, slice):
                x_indices_size = np.sum(x_indices.stop - x_indices.start)
            else:  # is tuple of indices
                x_indices_size = len(x_indices)
            if x_indices_size > max_x_indices:
                max_x_indices = x_indices_size

        # Cache which y src_bounds areas and weights are within grid bounds
        cached_y_indices = []
        cached_weights = []
        max_y_indices = 0
        for j, (y_0, y_1) in enumerate(grid_y_bounds):
            # Reverse lower and upper if dest grid is decreasing.
            if grid_y_decreasing:
                y_0, y_1 = y_1, y_0
            y_bounds, y_indices = _cropped_bounds(src_y_bounds, y_0, y_1)
            cached_y_indices.append(y_indices)
            # Keep record of the largest slice
            if isinstance(y_indices, slice):
                y_indices_size = np.sum(y_indices.stop - y_indices.start)
            else:  # is tuple of indices
                y_indices_size = len(y_indices)
            if y_indices_size > max_y_indices:
                max_y_indices = y_indices_size

            weights_i = []
            for i, (x_0, x_1) in enumerate(grid_x_bounds):
                # Reverse lower and upper if dest grid is decreasing.
                if grid_x_decreasing:
                    x_0, x_1 = x_1, x_0
                x_bounds = cached_x_bounds[i]
                x_indices = cached_x_indices[i]

                # Determine whether element i, j overlaps with src and hence
                # an area weight should be computed.
                # If x_0 > x_1 then we want [0]->x_1 and x_0->[0] + mod in the case
                # of wrapped longitudes. However if the src grid is not global
                # (i.e. circular) this new cell would include a region outside of
                # the extent of the src grid and thus the weight is therefore
                # invalid.
                outside_extent = x_0 > x_1 and not circular
                if (
                    outside_extent
                    or not y_within_bounds[j]
                    or not x_within_bounds[i]
                ):
                    weights = False
                else:
                    # Calculate weights based on areas of cropped bounds.
                    if isinstance(x_indices, tuple) and isinstance(
                        y_indices, tuple
                    ):
                        raise RuntimeError(
                            "Cannot handle split bounds " "in both x and y."
                        )
                    weights = area_func(y_bounds, x_bounds)
                weights_i.append(weights)
            cached_weights.append(weights_i)
        return (
            tuple(cached_x_indices),
            tuple(cached_y_indices),
            max_x_indices,
            max_y_indices,
            tuple(cached_weights),
        )

    weights_info = _calculate_regrid_area_weighted_weights(
        src_x_bounds,
        src_y_bounds,
        grid_x_bounds,
        grid_y_bounds,
        grid_x_decreasing,
        grid_y_decreasing,
        area_func,
        circular,
    )
    (
        cached_x_indices,
        cached_y_indices,
        max_x_indices,
        max_y_indices,
        cached_weights,
    ) = weights_info
    # Delete variables that are not needed and would not be available
    # if _calculate_regrid_area_weighted_weights was refactored further
    del src_x_bounds, src_y_bounds, grid_x_bounds, grid_y_bounds
    del grid_x_decreasing, grid_y_decreasing
    del area_func, circular

    # Ensure we have x_dim and y_dim.
    x_dim_orig = x_dim
    y_dim_orig = y_dim
    if y_dim is None:
        src_data = np.expand_dims(src_data, axis=src_data.ndim)
        y_dim = src_data.ndim - 1
    if x_dim is None:
        src_data = np.expand_dims(src_data, axis=src_data.ndim)
        x_dim = src_data.ndim - 1
    # Move y_dim and x_dim to last dimensions
    if not x_dim == src_data.ndim - 1:
        src_data = np.moveaxis(src_data, x_dim, -1)
    if not y_dim == src_data.ndim - 2:
        if x_dim < y_dim:
            # note: y_dim was shifted along by one position when
            # x_dim was moved to the last dimension
            src_data = np.moveaxis(src_data, y_dim - 1, -2)
        elif x_dim > y_dim:
            src_data = np.moveaxis(src_data, y_dim, -2)
    x_dim = src_data.ndim - 1
    y_dim = src_data.ndim - 2

    # Create empty "pre-averaging" data array that will enable the
    # src_data data coresponding to a given target grid point,
    # to be stacked per point.
    # Note that dtype is not preserved and that the array mask
    # allows for regions that do not overlap.
    new_shape = list(src_data.shape)
    new_shape[x_dim] = len(cached_x_indices)
    new_shape[y_dim] = len(cached_y_indices)
    num_target_pts = len(cached_y_indices) * len(cached_x_indices)
    src_areas_shape = list(src_data.shape)
    src_areas_shape[y_dim] = max_y_indices
    src_areas_shape[x_dim] = max_x_indices
    src_areas_shape += [num_target_pts]
    # Use input cube dtype or convert values to the smallest possible float
    # dtype when necessary.
    dtype = np.promote_types(src_data.dtype, np.float16)
    # Create empty arrays to hold src_data per target point, and weights
    src_area_datas = np.zeros(src_areas_shape, dtype=np.float64)
    src_area_weights = np.zeros(
        list((max_y_indices, max_x_indices, num_target_pts))
    )

    # Flag to indicate whether the original data was a masked array.
    src_masked = src_data.mask.any() if ma.isMaskedArray(src_data) else False
    if src_masked:
        src_area_masks = np.full(src_areas_shape, True, dtype=np.bool)
    else:
        new_data_mask = np.full(new_shape, False, dtype=np.bool)

    # Axes of data over which the weighted mean is calculated.
    axis = (y_dim, x_dim)

    # Stack the src_area data and weights for each target point
    target_pt_ji = -1
    for j, y_indices in enumerate(cached_y_indices):
        for i, x_indices in enumerate(cached_x_indices):
            target_pt_ji += 1
            # Determine whether to mask element i, j based on whether
            # there are valid weights.
            weights = cached_weights[j][i]
            if isinstance(weights, bool) and not weights:
                if not src_masked:
                    # Cheat! Fill the data with zeros and weights as one.
                    # The weighted average result will be the same, but
                    # we avoid dividing by zero.
                    src_area_weights[..., target_pt_ji] = 1
                    new_data_mask[..., j, i] = True
            else:
                # Calculate weighted mean of data points.
                # Slice out relevant data (this may or may not be a view()
                # depending on x_indices being a slice or not).
                data = src_data[..., y_indices, x_indices]
                len_x = data.shape[-1]
                len_y = data.shape[-2]
                src_area_datas[..., 0:len_y, 0:len_x, target_pt_ji] = data
                src_area_weights[0:len_y, 0:len_x, target_pt_ji] = weights
                if src_masked:
                    src_area_masks[
                        ..., 0:len_y, 0:len_x, target_pt_ji
                    ] = data.mask

    # Broadcast the weights array to allow numpy's ma.average
    # to be called.
    # Assign new shape to raise error on copy.
    src_area_weights.shape = src_area_datas.shape[-3:]
    # Broadcast weights to match shape of data.
    _, src_area_weights = np.broadcast_arrays(src_area_datas, src_area_weights)

    # Mask the data points
    if src_masked:
        src_area_datas = np.ma.array(src_area_datas, mask=src_area_masks)

    # Calculate weighted mean taking into account missing data.
    new_data = _weighted_mean_with_mdtol(
        src_area_datas, weights=src_area_weights, axis=axis, mdtol=mdtol
    )
    new_data = new_data.reshape(new_shape)
    if src_masked:
        new_data_mask = new_data.mask

    # Mask the data if originally masked or if the result has masked points
    if ma.isMaskedArray(src_data):
        new_data = ma.array(
            new_data,
            mask=new_data_mask,
            fill_value=src_data.fill_value,
            dtype=dtype,
        )
    elif new_data_mask.any():
        new_data = ma.array(new_data, mask=new_data_mask, dtype=dtype)
    else:
        new_data = new_data.astype(dtype)

    # Restore data to original form
    if x_dim_orig is None and y_dim_orig is None:
        new_data = np.squeeze(new_data, axis=x_dim)
        new_data = np.squeeze(new_data, axis=y_dim)
    elif y_dim_orig is None:
        new_data = np.squeeze(new_data, axis=y_dim)
        new_data = np.moveaxis(new_data, -1, x_dim_orig)
    elif x_dim_orig is None:
        new_data = np.squeeze(new_data, axis=x_dim)
        new_data = np.moveaxis(new_data, -1, y_dim_orig)
    elif x_dim_orig < y_dim_orig:
        # move the x_dim back first, so that the y_dim will
        # then be moved to its original position
        new_data = np.moveaxis(new_data, -1, x_dim_orig)
        new_data = np.moveaxis(new_data, -1, y_dim_orig)
    else:
        # move the y_dim back first, so that the x_dim will
        # then be moved to its original position
        new_data = np.moveaxis(new_data, -2, y_dim_orig)
        new_data = np.moveaxis(new_data, -1, x_dim_orig)

    return new_data


def regrid_area_weighted_rectilinear_src_and_grid(
    src_cube, grid_cube, mdtol=0
):
    """
    Return a new cube with data values calculated using the area weighted
    mean of data values from src_grid regridded onto the horizontal grid of
    grid_cube.

    This function requires that the horizontal grids of both cubes are
    rectilinear (i.e. expressed in terms of two orthogonal 1D coordinates)
    and that these grids are in the same coordinate system. This function
    also requires that the coordinates describing the horizontal grids
    all have bounds.

    .. note::

        Elements in data array of the returned cube that lie either partially
        or entirely outside of the horizontal extent of the src_cube will
        be masked irrespective of the value of mdtol.

    Args:

    * src_cube:
        An instance of :class:`iris.cube.Cube` that supplies the data,
        metadata and coordinates.
    * grid_cube:
        An instance of :class:`iris.cube.Cube` that supplies the desired
        horizontal grid definition.

    Kwargs:

    * mdtol:
        Tolerance of missing data. The value returned in each element of the
        returned cube's data array will be masked if the fraction of masked
        data in the overlapping cells of the source cube exceeds mdtol. This
        fraction is calculated based on the area of masked cells within each
        target cell. mdtol=0 means no missing data is tolerated while mdtol=1
        will mean the resulting element will be masked if and only if all the
        overlapping cells of the source cube are masked. Defaults to 0.

    Returns:
        A new :class:`iris.cube.Cube` instance.

    """
    regrid_info = _regrid_area_weighted_rectilinear_src_and_grid__prepare(
        src_cube, grid_cube
    )
    result = _regrid_area_weighted_rectilinear_src_and_grid__perform(
        src_cube, regrid_info, mdtol
    )
    return result


def _regrid_area_weighted_rectilinear_src_and_grid__prepare(
    src_cube, grid_cube
):
    """
    First (setup) part of 'regrid_area_weighted_rectilinear_src_and_grid'.

    Check inputs and calculate related info. The 'regrid info' returned
    can be re-used over many 2d slices.

    """
    # Get the 1d monotonic (or scalar) src and grid coordinates.
    src_x, src_y = _get_xy_coords(src_cube)
    grid_x, grid_y = _get_xy_coords(grid_cube)

    # Condition 1: All x and y coordinates must have contiguous bounds to
    # define areas.
    if (
        not src_x.is_contiguous()
        or not src_y.is_contiguous()
        or not grid_x.is_contiguous()
        or not grid_y.is_contiguous()
    ):
        raise ValueError(
            "The horizontal grid coordinates of both the source "
            "and grid cubes must have contiguous bounds."
        )

    # Condition 2: Everything must have the same coordinate system.
    src_cs = src_x.coord_system
    grid_cs = grid_x.coord_system
    if src_cs != grid_cs:
        raise ValueError(
            "The horizontal grid coordinates of both the source "
            "and grid cubes must have the same coordinate "
            "system."
        )

    # Condition 3: cannot create vector coords from scalars.
    src_x_dims = src_cube.coord_dims(src_x)
    src_x_dim = None
    if src_x_dims:
        src_x_dim = src_x_dims[0]
    src_y_dims = src_cube.coord_dims(src_y)
    src_y_dim = None
    if src_y_dims:
        src_y_dim = src_y_dims[0]
    if (
        src_x_dim is None
        and grid_x.shape[0] != 1
        or src_y_dim is None
        and grid_y.shape[0] != 1
    ):
        raise ValueError(
            "The horizontal grid coordinates of source cube "
            "includes scalar coordinates, but the new grid does "
            "not. The new grid must not require additional data "
            "dimensions to be created."
        )

    # Determine whether to calculate flat or spherical areas.
    # Don't only rely on coord system as it may be None.
    spherical = (
        isinstance(
            src_cs,
            (iris.coord_systems.GeogCS, iris.coord_systems.RotatedGeogCS),
        )
        or src_x.units == "degrees"
        or src_x.units == "radians"
    )

    # Get src and grid bounds in the same units.
    x_units = cf_units.Unit("radians") if spherical else src_x.units
    y_units = cf_units.Unit("radians") if spherical else src_y.units

    # Operate in highest precision.
    src_dtype = np.promote_types(src_x.bounds.dtype, src_y.bounds.dtype)
    grid_dtype = np.promote_types(grid_x.bounds.dtype, grid_y.bounds.dtype)
    dtype = np.promote_types(src_dtype, grid_dtype)

    src_x_bounds = _get_bounds_in_units(src_x, x_units, dtype)
    src_y_bounds = _get_bounds_in_units(src_y, y_units, dtype)
    grid_x_bounds = _get_bounds_in_units(grid_x, x_units, dtype)
    grid_y_bounds = _get_bounds_in_units(grid_y, y_units, dtype)

    # Create 2d meshgrids as required by _create_cube func.
    meshgrid_x, meshgrid_y = _meshgrid(grid_x.points, grid_y.points)

    # Determine whether target grid bounds are decreasing. This must
    # be determined prior to wrap_lons being called.
    grid_x_decreasing = grid_x_bounds[-1, 0] < grid_x_bounds[0, 0]
    grid_y_decreasing = grid_y_bounds[-1, 0] < grid_y_bounds[0, 0]

    # Wrapping of longitudes.
    if spherical:
        base = np.min(src_x_bounds)
        modulus = x_units.modulus
        # Only wrap if necessary to avoid introducing floating
        # point errors.
        if np.min(grid_x_bounds) < base or np.max(grid_x_bounds) > (
            base + modulus
        ):
            grid_x_bounds = iris.analysis.cartography.wrap_lons(
                grid_x_bounds, base, modulus
            )

    # Determine whether the src_x coord has periodic boundary conditions.
    circular = getattr(src_x, "circular", False)

    # Use simple cartesian area function or one that takes into
    # account the curved surface if coord system is spherical.
    if spherical:
        area_func = _spherical_area
    else:
        area_func = _cartesian_area

    return (src_x, src_y, src_x_dim, src_y_dim, src_x_bounds, src_y_bounds,
            grid_x, grid_y, grid_x_bounds, grid_y_bounds, grid_x_decreasing,
            grid_y_decreasing, meshgrid_x, meshgrid_y, area_func, circular)


def _regrid_area_weighted_rectilinear_src_and_grid__perform(
    src_cube, regrid_info, mdtol
):
    """
    Second (regrid) part of 'regrid_area_weighted_rectilinear_src_and_grid'.

    Perform the prepared regrid calculation on a single 2d cube.

    """
    (src_x, src_y, src_x_dim, src_y_dim, src_x_bounds, src_y_bounds, grid_x,
     grid_y, grid_x_bounds, grid_y_bounds, grid_x_decreasing,
     grid_y_decreasing, meshgrid_x, meshgrid_y, area_func, circular
     ) = regrid_info

    # Calculate new data array for regridded cube.
    new_data = _regrid_area_weighted_array(
        src_cube.data,
        src_x_dim,
        src_y_dim,
        src_x_bounds,
        src_y_bounds,
        grid_x_bounds,
        grid_y_bounds,
        grid_x_decreasing,
        grid_y_decreasing,
        area_func,
        circular,
        mdtol,
    )

    # Wrap up the data as a Cube.
    regrid_callback = RectilinearRegridder._regrid
    new_cube = RectilinearRegridder._create_cube(
        new_data,
        src_cube,
        src_x_dim,
        src_y_dim,
        src_x,
        src_y,
        grid_x,
        grid_y,
        meshgrid_x,
        meshgrid_y,
        regrid_callback,
    )

    # Slice out any length 1 dimensions.
    indices = [slice(None, None)] * new_data.ndim
    if src_x_dim is not None and new_cube.shape[src_x_dim] == 1:
        indices[src_x_dim] = 0
    if src_y_dim is not None and new_cube.shape[src_y_dim] == 1:
        indices[src_y_dim] = 0
    if 0 in indices:
        new_cube = new_cube[tuple(indices)]

    return new_cube


def regrid_weighted_curvilinear_to_rectilinear(src_cube, weights, grid_cube):
    r"""
    Return a new cube with the data values calculated using the weighted
    mean of data values from :data:`src_cube` and the weights from
    :data:`weights` regridded onto the horizontal grid of :data:`grid_cube`.

    This function requires that the :data:`src_cube` has a horizontal grid
    defined by a pair of X- and Y-axis coordinates which are mapped over the
    same cube dimensions, thus each point has an individually defined X and
    Y coordinate value.  The actual dimensions of these coordinates are of
    no significance.
    The :data:`src_cube` grid cube must have a normal horizontal grid,
    i.e. expressed in terms of two orthogonal 1D horizontal coordinates.
    Both grids must be in the same coordinate system, and the :data:`grid_cube`
    must have horizontal coordinates that are both bounded and contiguous.

    Note that, for any given target :data:`grid_cube` cell, only the points
    from the :data:`src_cube` that are bound by that cell will contribute to
    the cell result. The bounded extent of the :data:`src_cube` will not be
    considered here.

    A target :data:`grid_cube` cell result will be calculated as,
    :math:`\sum (src\_cube.data_{ij} * weights_{ij}) / \sum weights_{ij}`, for
    all :math:`ij` :data:`src_cube` points that are bound by that cell.

    .. warning::

        * All coordinates that span the :data:`src_cube` that don't define
          the horizontal curvilinear grid will be ignored.

    Args:

    * src_cube:
        A :class:`iris.cube.Cube` instance that defines the source
        variable grid to be regridded.
    * weights (array or None):
        A :class:`numpy.ndarray` instance that defines the weights
        for the source variable grid cells. Must have the same shape
        as the X and Y coordinates.  If weights is None, all-ones will be used.
    * grid_cube:
        A :class:`iris.cube.Cube` instance that defines the target
        rectilinear grid.

    Returns:
        A :class:`iris.cube.Cube` instance.

    """
    regrid_info = _regrid_weighted_curvilinear_to_rectilinear__prepare(
        src_cube, weights, grid_cube
    )
    result = _regrid_weighted_curvilinear_to_rectilinear__perform(
        src_cube, regrid_info
    )
    return result


class PointInCell:
    """
    This class describes the point-in-cell regridding scheme for use
    typically with :meth:`iris.cube.Cube.regrid()`.

    .. warning::

        This class is now **disabled**.

        The functionality has been moved to
        :class:`iris.analysis.PointInCell`.

    """

    def __init__(self, weights=None):
        """
        Point-in-cell regridding scheme suitable for regridding over one
        or more orthogonal coordinates.

        .. warning::

            This class is now **disabled**.

            The functionality has been moved to
            :class:`iris.analysis.PointInCell`.

        """
        raise Exception(
            'The class "iris.experimental.PointInCell" has been '
            "moved, and is now in iris.analysis"
            "\nPlease replace "
            '"iris.experimental.PointInCell" with '
            '"iris.analysis.PointInCell".'
        )


class _ProjectedUnstructuredRegridder:
    """
    This class provides regridding that uses scipy.interpolate.griddata.

    """

    def __init__(self, src_cube, tgt_grid_cube, method, projection=None):
        """
        Create a regridder for conversions between the source
        and target grids.

        Args:

        * src_cube:
            The :class:`~iris.cube.Cube` providing the source points.
        * tgt_grid_cube:
            The :class:`~iris.cube.Cube` providing the target grid.
        * method:
            Either 'linear' or 'nearest'.
        * projection:
            The projection in which the interpolation is performed. If None, a
            PlateCarree projection is used. Defaults to None.

        """
        # Validity checks.
        if not isinstance(src_cube, iris.cube.Cube):
            raise TypeError("'src_cube' must be a Cube")
        if not isinstance(tgt_grid_cube, iris.cube.Cube):
            raise TypeError("'tgt_grid_cube' must be a Cube")

        # Snapshot the state of the target cube to ensure that the regridder
        # is impervious to external changes to the original source cubes.
        self._tgt_grid = snapshot_grid(tgt_grid_cube)

        # Check the target grid units.
        for coord in self._tgt_grid:
            self._check_units(coord)

        # Whether to use linear or nearest-neighbour interpolation.
        if method not in ("linear", "nearest"):
            msg = "Regridding method {!r} not supported.".format(method)
            raise ValueError(msg)
        self._method = method

        src_x_coord, src_y_coord = get_xy_coords(src_cube)
        if src_x_coord.coord_system != src_y_coord.coord_system:
            raise ValueError(
                "'src_cube' lateral geographic coordinates have "
                "differing coordinate sytems."
            )
        if src_x_coord.coord_system is None:
            raise ValueError(
                "'src_cube' lateral geographic coordinates have "
                "no coordinate sytem."
            )
        tgt_x_coord, tgt_y_coord = get_xy_dim_coords(tgt_grid_cube)
        if tgt_x_coord.coord_system != tgt_y_coord.coord_system:
            raise ValueError(
                "'tgt_grid_cube' lateral geographic coordinates "
                "have differing coordinate sytems."
            )
        if tgt_x_coord.coord_system is None:
            raise ValueError(
                "'tgt_grid_cube' lateral geographic coordinates "
                "have no coordinate sytem."
            )

        if projection is None:
            globe = src_x_coord.coord_system.as_cartopy_globe()
            projection = ccrs.Sinusoidal(globe=globe)
        self._projection = projection

    def _check_units(self, coord):
        if coord.coord_system is None:
            # No restriction on units.
            pass
        elif isinstance(
            coord.coord_system,
            (iris.coord_systems.GeogCS, iris.coord_systems.RotatedGeogCS),
        ):
            # Units for lat-lon or rotated pole must be 'degrees'. Note
            # that 'degrees_east' etc. are equal to 'degrees'.
            if coord.units != "degrees":
                msg = (
                    "Unsupported units for coordinate system. "
                    "Expected 'degrees' got {!r}.".format(coord.units)
                )
                raise ValueError(msg)
        else:
            # Units for other coord systems must be equal to metres.
            if coord.units != "m":
                msg = (
                    "Unsupported units for coordinate system. "
                    "Expected 'metres' got {!r}.".format(coord.units)
                )
                raise ValueError(msg)

    @staticmethod
    def _regrid(
        src_data,
        xy_dim,
        src_x_coord,
        src_y_coord,
        tgt_x_coord,
        tgt_y_coord,
        projection,
        method,
    ):
        """
        Regrids input data from the source to the target. Calculation is.

        """
        # Transform coordinates into the projection the interpolation will be
        # performed in.
        src_projection = src_x_coord.coord_system.as_cartopy_projection()
        projected_src_points = projection.transform_points(
            src_projection, src_x_coord.points, src_y_coord.points
        )

        tgt_projection = tgt_x_coord.coord_system.as_cartopy_projection()
        tgt_x, tgt_y = _meshgrid(tgt_x_coord.points, tgt_y_coord.points)
        projected_tgt_grid = projection.transform_points(
            tgt_projection, tgt_x, tgt_y
        )

        # Prepare the result data array.
        # XXX TODO: Deal with masked src_data
        (tgt_y_shape,) = tgt_y_coord.shape
        (tgt_x_shape,) = tgt_x_coord.shape
        tgt_shape = (
            src_data.shape[:xy_dim]
            + (tgt_y_shape,)
            + (tgt_x_shape,)
            + src_data.shape[xy_dim + 1 :]
        )
        data = np.empty(tgt_shape, dtype=src_data.dtype)

        iter_shape = list(src_data.shape)
        iter_shape[xy_dim] = 1

        for index in np.ndindex(tuple(iter_shape)):
            src_index = list(index)
            src_index[xy_dim] = slice(None)
            src_subset = src_data[tuple(src_index)]
            tgt_index = (
                index[:xy_dim]
                + (slice(None), slice(None))
                + index[xy_dim + 1 :]
            )
            data[tgt_index] = scipy.interpolate.griddata(
                projected_src_points[..., :2],
                src_subset,
                (projected_tgt_grid[..., 0], projected_tgt_grid[..., 1]),
                method=method,
            )
        data = np.ma.array(data, mask=np.isnan(data))
        return data

    def _create_cube(
        self,
        data,
        src,
        src_xy_dim,
        src_x_coord,
        src_y_coord,
        grid_x_coord,
        grid_y_coord,
        regrid_callback,
    ):
        """
        Return a new Cube for the result of regridding the source Cube onto
        the new grid.

        All the metadata and coordinates of the result Cube are copied from
        the source Cube, with two exceptions:
            - Grid dimension coordinates are copied from the grid Cube.
            - Auxiliary coordinates which span the grid dimensions are
              ignored, except where they provide a reference surface for an
              :class:`iris.aux_factory.AuxCoordFactory`.

        Args:

        * data:
            The regridded data as an N-dimensional NumPy array.
        * src:
            The source Cube.
        * src_xy_dim:
            The dimension the X and Y coord span within the source Cube.
        * src_x_coord:
            The X coordinate (either :class:`iris.coords.AuxCoord` or
            :class:`iris.coords.DimCoord`).
        * src_y_coord:
            The Y coordinate (either :class:`iris.coords.AuxCoord` or
            :class:`iris.coords.DimCoord`).
        * grid_x_coord:
            The :class:`iris.coords.DimCoord` for the new grid's X
            coordinate.
        * grid_y_coord:
            The :class:`iris.coords.DimCoord` for the new grid's Y
            coordinate.
        * regrid_callback:
            The routine that will be used to calculate the interpolated
            values of any reference surfaces.

        Returns:
            The new, regridded Cube.

        """
        # Create a result cube with the appropriate metadata
        result = iris.cube.Cube(data)
        result.metadata = copy.deepcopy(src.metadata)

        # Copy across all the coordinates which don't span the grid.
        # Record a mapping from old coordinate IDs to new coordinates,
        # for subsequent use in creating updated aux_factories.
        coord_mapping = {}

        def copy_coords(src_coords, add_method):
            for coord in src_coords:
                dims = src.coord_dims(coord)
                if coord is src_x_coord:
                    coord = grid_x_coord
                    # Increase dimensionality to account for 1D coord being
                    # regridded onto 2D grid
                    dims = list(dims)
                    dims[0] += 1
                    dims = tuple(dims)
                    add_method = result.add_dim_coord
                elif coord is src_y_coord:
                    coord = grid_y_coord
                    add_method = result.add_dim_coord
                elif src_xy_dim in dims:
                    continue
                result_coord = coord.copy()
                add_method(result_coord, dims)
                coord_mapping[id(coord)] = result_coord

        copy_coords(src.dim_coords, result.add_dim_coord)
        copy_coords(src.aux_coords, result.add_aux_coord)

        def regrid_reference_surface(
            src_surface_coord,
            surface_dims,
            src_xy_dim,
            src_x_coord,
            src_y_coord,
            grid_x_coord,
            grid_y_coord,
            regrid_callback,
        ):
            # Determine which of the reference surface's dimensions span the X
            # and Y dimensions of the source cube.
            surface_xy_dim = surface_dims.index(src_xy_dim)
            surface = regrid_callback(
                src_surface_coord.points,
                surface_xy_dim,
                src_x_coord,
                src_y_coord,
                grid_x_coord,
                grid_y_coord,
            )
            surface_coord = src_surface_coord.copy(surface)
            return surface_coord

        # Copy across any AuxFactory instances, and regrid their reference
        # surfaces where required.
        for factory in src.aux_factories:
            for coord in factory.dependencies.values():
                if coord is None:
                    continue
                dims = src.coord_dims(coord)
                if src_xy_dim in dims:
                    result_coord = regrid_reference_surface(
                        coord,
                        dims,
                        src_xy_dim,
                        src_x_coord,
                        src_y_coord,
                        grid_x_coord,
                        grid_y_coord,
                        regrid_callback,
                    )
                    result.add_aux_coord(result_coord, (dims[0], dims[0] + 1))
                    coord_mapping[id(coord)] = result_coord
            try:
                result.add_aux_factory(factory.updated(coord_mapping))
            except KeyError:
                msg = (
                    "Cannot update aux_factory {!r} because of dropped"
                    " coordinates.".format(factory.name())
                )
                warnings.warn(msg)
        return result

    def __call__(self, src_cube):
        """
        Regrid this :class:`~iris.cube.Cube` on to the target grid of
        this :class:`UnstructuredProjectedRegridder`.

        The given cube must be defined with the same grid as the source
        grid used to create this :class:`UnstructuredProjectedRegridder`.

        Args:

        * src_cube:
            A :class:`~iris.cube.Cube` to be regridded.

        Returns:
            A cube defined with the horizontal dimensions of the target
            and the other dimensions from this cube. The data values of
            this cube will be converted to values on the new grid using
            either nearest-neighbour or linear interpolation.

        """
        # Validity checks.
        if not isinstance(src_cube, iris.cube.Cube):
            raise TypeError("'src' must be a Cube")

        src_x_coord, src_y_coord = get_xy_coords(src_cube)
        tgt_x_coord, tgt_y_coord = self._tgt_grid
        src_cs = src_x_coord.coord_system

        if src_x_coord.coord_system != src_y_coord.coord_system:
            raise ValueError(
                "'src' lateral geographic coordinates have "
                "differing coordinate sytems."
            )
        if src_cs is None:
            raise ValueError(
                "'src' lateral geographic coordinates have "
                "no coordinate sytem."
            )

        # Check the source grid units.
        for coord in (src_x_coord, src_y_coord):
            self._check_units(coord)

        (src_x_dim,) = src_cube.coord_dims(src_x_coord)
        (src_y_dim,) = src_cube.coord_dims(src_y_coord)

        if src_x_dim != src_y_dim:
            raise ValueError(
                "'src' lateral geographic coordinates should map "
                "the same dimension."
            )
        src_xy_dim = src_x_dim

        # Compute the interpolated data values.
        data = self._regrid(
            src_cube.data,
            src_xy_dim,
            src_x_coord,
            src_y_coord,
            tgt_x_coord,
            tgt_y_coord,
            self._projection,
            method=self._method,
        )

        # Wrap up the data as a Cube.
        regrid_callback = functools.partial(
            self._regrid, method=self._method, projection=self._projection
        )

        new_cube = self._create_cube(
            data,
            src_cube,
            src_xy_dim,
            src_x_coord,
            src_y_coord,
            tgt_x_coord,
            tgt_y_coord,
            regrid_callback,
        )

        return new_cube


class ProjectedUnstructuredLinear:
    """
    This class describes the linear regridding scheme which uses the
    scipy.interpolate.griddata to regrid unstructured data on to a grid.

    The source cube and the target cube will be projected into a common
    projection for the scipy calculation to be performed.

    """

    def __init__(self, projection=None):
        """
        Linear regridding scheme that uses scipy.interpolate.griddata on
        projected unstructured data.

        Optional Args:

        * projection: `cartopy.crs instance`
            The projection that the scipy calculation is performed in.
            If None is given, a PlateCarree projection is used. Defaults to
            None.

        """
        self.projection = projection

    def regridder(self, src_cube, target_grid):
        """
        Creates a linear regridder to perform regridding, using
        scipy.interpolate.griddata from unstructured source points to the
        target grid. The regridding calculation is performed in the given
        projection.

        Typically you should use :meth:`iris.cube.Cube.regrid` for
        regridding a cube. There are, however, some situations when
        constructing your own regridder is preferable. These are detailed in
        the :ref:`user guide <caching_a_regridder>`.

        Args:

        * src_cube:
            The :class:`~iris.cube.Cube` defining the unstructured source
            points.
        * target_grid:
            The :class:`~iris.cube.Cube` defining the target grid.

        Returns:
            A callable with the interface:

                `callable(cube)`

            where `cube` is a cube with the same grid as `src_cube`
            that is to be regridded to the `target_grid`.

        """
        return _ProjectedUnstructuredRegridder(
            src_cube, target_grid, "linear", self.projection
        )


class ProjectedUnstructuredNearest:
    """
    This class describes the nearest regridding scheme which uses the
    scipy.interpolate.griddata to regrid unstructured data on to a grid.

    The source cube and the target cube will be projected into a common
    projection for the scipy calculation to be performed.

    .. Note::
          The :class:`iris.analysis.UnstructuredNearest` scheme performs
          essentially the same job.  That calculation is more rigorously
          correct and may be applied to larger data regions (including global).
          This one however, where applicable, is substantially faster.

    """

    def __init__(self, projection=None):
        """
        Nearest regridding scheme that uses scipy.interpolate.griddata on
        projected unstructured data.

        Optional Args:

        * projection: `cartopy.crs instance`
            The projection that the scipy calculation is performed in.
            If None is given, a PlateCarree projection is used. Defaults to
            None.

        """
        self.projection = projection

    def regridder(self, src_cube, target_grid):
        """
        Creates a nearest-neighbour regridder to perform regridding, using
        scipy.interpolate.griddata from unstructured source points to the
        target grid. The regridding calculation is performed in the given
        projection.

        Typically you should use :meth:`iris.cube.Cube.regrid` for
        regridding a cube. There are, however, some situations when
        constructing your own regridder is preferable. These are detailed in
        the :ref:`user guide <caching_a_regridder>`.

        Args:

        * src_cube:
            The :class:`~iris.cube.Cube` defining the unstructured source
            points.
        * target_grid:
            The :class:`~iris.cube.Cube` defining the target grid.

        Returns:
            A callable with the interface:

                `callable(cube)`

            where `cube` is a cube with the same grid as `src_cube`
            that is to be regridded to the `target_grid`.

        """
        return _ProjectedUnstructuredRegridder(
            src_cube, target_grid, "nearest", self.projection
        )
