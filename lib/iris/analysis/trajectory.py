# (C) British Crown Copyright 2010 - 2016, Met Office
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
Defines a Trajectory class, and a routine to extract a sub-cube along a
trajectory.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six

import math

import numpy as np

from cf_units import Unit
import iris.analysis
import iris.coord_systems
import iris.coords

from iris.analysis._interpolate_private import \
    _nearest_neighbour_indices_ndcoords, linear as linear_regrid
from iris.analysis._interpolation import snapshot_grid


class _Segment(object):
    """A single trajectory line segment: Two points, as described in the
    Trajectory class."""
    def __init__(self, p0, p1):
        # check keys
        if sorted(p0.keys()) != sorted(p1.keys()):
            raise ValueError("keys do not match")

        self.pts = [p0, p1]

        # calculate our length
        squares = 0
        for key in self.pts[0].keys():
            delta = self.pts[1][key] - self.pts[0][key]
            squares += delta * delta
        self.length = math.sqrt(squares)


class Trajectory(object):
    """A series of given waypoints with pre-calculated sample points."""

    def __init__(self, waypoints, sample_count=10):
        """
        Defines a trajectory using a sequence of waypoints.

        For example::

            waypoints = [{'latitude': 45, 'longitude': -60},
                         {'latitude': 45, 'longitude': 0}]
            Trajectory(waypoints)

        .. note:: All the waypoint dictionaries must contain the same
        coordinate names.

        Args:

        * waypoints
            A sequence of dictionaries, mapping coordinate names to values.

        Kwargs:

        * sample_count
            The number of sample positions to use along the trajectory.

        """
        self.waypoints = waypoints
        self.sample_count = sample_count

        # create line segments from the waypoints
        segments = [_Segment(self.waypoints[i], self.waypoints[i+1])
                    for i in range(len(self.waypoints) - 1)]

        # calculate our total length
        self.length = sum([seg.length for seg in segments])

        # generate our sampled points
        #: The trajectory points, as dictionaries of {coord_name: value}.
        self.sampled_points = []
        sample_step = self.length / (self.sample_count - 1)

        # start with the first segment
        cur_seg_i = 0
        cur_seg = segments[cur_seg_i]
        len_accum = cur_seg.length
        for p in range(self.sample_count):

            # calculate the sample position along our total length
            sample_at_len = p * sample_step

            # skip forward to the containing segment
            while len_accum < sample_at_len and cur_seg_i < len(segments):
                cur_seg_i += 1
                cur_seg = segments[cur_seg_i]
                len_accum += cur_seg.length

            # how far through the segment is our sample point?
            seg_start_len = len_accum - cur_seg.length
            seg_frac = (sample_at_len-seg_start_len) / cur_seg.length

            # sample each coordinate in this segment, to create a new
            # sampled point
            new_sampled_point = {}
            for key in cur_seg.pts[0].keys():
                seg_coord_delta = cur_seg.pts[1][key] - cur_seg.pts[0][key]
                new_sampled_point.update({key: cur_seg.pts[0][key] +
                                         seg_frac*seg_coord_delta})

            # add this new sampled point
            self.sampled_points.append(new_sampled_point)

    def __repr__(self):
        return 'Trajectory(%s, sample_count=%s)' % (self.waypoints,
                                                    self.sample_count)


def interpolate(cube, sample_points, method=None):
    """
    Extract a sub-cube at the given n-dimensional points.

    Args:

    * cube
        The source Cube.

    * sample_points
        A sequence of coordinate (name) - values pairs.

    Kwargs:

    * method
        Request "linear" interpolation (default) or "nearest" neighbour.
        Only nearest neighbour is available when specifying multi-dimensional
        coordinates.


    For example::

        sample_points = [('latitude', [45, 45, 45]),
        ('longitude', [-60, -50, -40])]
        interpolated_cube = interpolate(cube, sample_points)

    """
    if method not in [None, "linear", "nearest"]:
        raise ValueError("Unhandled interpolation specified : %s" % method)

    # Convert any coordinate names to coords
    points = []
    for coord, values in sample_points:
        if isinstance(coord, six.string_types):
            coord = cube.coord(coord)
        points.append((coord, values))
    sample_points = points

    # Do all value sequences have the same number of values?
    coord, values = sample_points[0]
    trajectory_size = len(values)
    for coord, values in sample_points[1:]:
        if len(values) != trajectory_size:
            raise ValueError('Lengths of coordinate values are inconsistent.')

    # Which dimensions are we squishing into the last dimension?
    squish_my_dims = set()
    for coord, values in sample_points:
        dims = cube.coord_dims(coord)
        for dim in dims:
            squish_my_dims.add(dim)

    # Derive the new cube's shape by filtering out all the dimensions we're
    # about to sample,
    # and then adding a new dimension to accommodate all the sample points.
    remaining = [(dim, size) for dim, size in enumerate(cube.shape) if dim
                 not in squish_my_dims]
    new_data_shape = [size for dim, size in remaining]
    new_data_shape.append(trajectory_size)

    # Start with empty data and then fill in the "column" of values for each
    # trajectory point.
    new_cube = iris.cube.Cube(np.empty(new_data_shape))
    new_cube.metadata = cube.metadata

    # Derive the mapping from the non-trajectory source dimensions to their
    # corresponding destination dimensions.
    remaining_dims = [dim for dim, size in remaining]
    dimension_remap = {dim: i for i, dim in enumerate(remaining_dims)}

    # Record a mapping from old coordinate IDs to new coordinates,
    # for subsequent use in creating updated aux_factories.
    coord_mapping = {}

    # Create all the non-squished coords
    for coord in cube.dim_coords:
        src_dims = cube.coord_dims(coord)
        if squish_my_dims.isdisjoint(src_dims):
            dest_dims = [dimension_remap[dim] for dim in src_dims]
            new_coord = coord.copy()
            new_cube.add_dim_coord(new_coord, dest_dims)
            coord_mapping[id(coord)] = new_coord
    for coord in cube.aux_coords:
        src_dims = cube.coord_dims(coord)
        if squish_my_dims.isdisjoint(src_dims):
            dest_dims = [dimension_remap[dim] for dim in src_dims]
            new_coord = coord.copy()
            new_cube.add_aux_coord(new_coord, dest_dims)
            coord_mapping[id(coord)] = new_coord

    # Create all the squished (non derived) coords, not filled in yet.
    trajectory_dim = len(remaining_dims)
    for coord in cube.dim_coords + cube.aux_coords:
        src_dims = cube.coord_dims(coord)
        if not squish_my_dims.isdisjoint(src_dims):
            points = np.array([coord.points.flatten()[0]] * trajectory_size)
            new_coord = iris.coords.AuxCoord(points,
                                             standard_name=coord.standard_name,
                                             long_name=coord.long_name,
                                             units=coord.units,
                                             bounds=None,
                                             attributes=coord.attributes,
                                             coord_system=coord.coord_system)
            new_cube.add_aux_coord(new_coord, trajectory_dim)
            coord_mapping[id(coord)] = new_coord

    for factory in cube.aux_factories:
        new_cube.add_aux_factory(factory.updated(coord_mapping))

    # Are the given coords all 1-dimensional? (can we do linear interp?)
    for coord, values in sample_points:
        if coord.ndim > 1:
            if method == "linear":
                msg = "Cannot currently perform linear interpolation for " \
                      "multi-dimensional coordinates."
                raise iris.exceptions.CoordinateMultiDimError(msg)
            method = "nearest"
            break

    if method in ["linear", None]:
        for i in range(trajectory_size):
            point = [(coord, values[i]) for coord, values in sample_points]
            column = linear_regrid(cube, point)
            new_cube.data[..., i] = column.data
            # Fill in the empty squashed (non derived) coords.
            for column_coord in column.dim_coords + column.aux_coords:
                src_dims = cube.coord_dims(column_coord)
                if not squish_my_dims.isdisjoint(src_dims):
                    if len(column_coord.points) != 1:
                        msg = "Expected to find exactly one point. Found {}."
                        raise Exception(msg.format(column_coord.points))
                    new_cube.coord(column_coord.name()).points[i] = \
                        column_coord.points[0]

    elif method == "nearest":
        # Use a cache with _nearest_neighbour_indices_ndcoords()
        cache = {}
        column_indexes = _nearest_neighbour_indices_ndcoords(
            cube, sample_points, cache=cache)

        # Construct "fancy" indexes, so we can create the result data array in
        # a single numpy indexing operation.
        # ALSO: capture the index range in each dimension, so that we can fetch
        # only a required (square) sub-region of the source data.
        fancy_source_indices = []
        region_slices = []
        n_index_length = len(column_indexes[0])
        dims_reduced = [False] * n_index_length
        for i_ind in range(n_index_length):
            contents = [column_index[i_ind]
                        for column_index in column_indexes]
            each_used = [content != slice(None) for content in contents]
            if np.all(each_used):
                # This dimension is addressed : use a list of indices.
                dims_reduced[i_ind] = True
                # Select the region by min+max indices.
                start_ind = np.min(contents)
                stop_ind = 1 + np.max(contents)
                region_slice = slice(start_ind, stop_ind)
                # Record point indices with start subtracted from all of them.
                fancy_index = list(np.array(contents) - start_ind)
            elif not np.any(each_used):
                # This dimension is not addressed by the operation.
                # Use a ":" as the index.
                fancy_index = slice(None)
                # No sub-region selection for this dimension.
                region_slice = slice(None)
            else:
                # Should really never happen, if _ndcoords is right.
                msg = ('Internal error in trajectory interpolation : point '
                       'selection indices should all have the same form.')
                raise ValueError(msg)

            fancy_source_indices.append(fancy_index)
            region_slices.append(region_slice)

        # Fetch the required (square-section) region of the source data.
        # NOTE: This is not quite as good as only fetching the individual
        # points used, but it avoids creating a sub-cube for each point,
        # which is very slow, especially when points are re-used a lot ...
        source_area_indices = tuple(region_slices)
        source_data = cube[source_area_indices].data

        # Transpose source data before indexing it to get the final result.
        # Because.. the fancy indexing will replace the indexed (horizontal)
        # dimensions with a new single dimension over trajectory points.
        # Move those dimensions to the end *first* : this ensures that the new
        # dimension also appears at the end, which is where we want it.
        # Make a list of dims with the reduced ones last.
        dims_reduced = np.array(dims_reduced)
        dims_order = np.arange(n_index_length)
        dims_order = np.concatenate((dims_order[~dims_reduced],
                                     dims_order[dims_reduced]))
        # Rearrange the data dimensions and the fancy indices into that order.
        source_data = source_data.transpose(dims_order)
        fancy_source_indices = [fancy_source_indices[i_dim]
                                for i_dim in dims_order]

        # Apply the fancy indexing to get all the result data points.
        source_data = source_data[fancy_source_indices]

        # "Fix" problems with missing datapoints producing odd values
        # when copied from a masked into an unmasked array.
        # TODO: proper masked data handling.
        if np.ma.isMaskedArray(source_data):
            # This is **not** proper mask handling, because we cannot produce a
            # masked result, but it ensures we use a "filled" version of the
            # input in this case.
            source_data = source_data.filled()
        new_cube.data[:] = source_data
        # NOTE: we assign to "new_cube.data[:]" and *not* just "new_cube.data",
        # because the existing code produces a default dtype from 'np.empty'
        # instead of preserving the input dtype.
        # TODO: maybe this should be fixed -- i.e. to preserve input dtype ??

        # Fill in the empty squashed (non derived) coords.
        column_coords = [coord
                         for coord in cube.dim_coords + cube.aux_coords
                         if not squish_my_dims.isdisjoint(
                             cube.coord_dims(coord))]
        new_cube_coords = [new_cube.coord(column_coord.name())
                           for column_coord in column_coords]
        all_point_indices = np.array(column_indexes)
        single_point_test_cube = cube[column_indexes[0]]
        for new_cube_coord, src_coord in zip(new_cube_coords, column_coords):
            # Check structure of the indexed coord (at one selected point).
            point_coord = single_point_test_cube.coord(src_coord)
            if len(point_coord.points) != 1:
                msg = ('Coord {} at one x-y position has the shape {}, '
                       'instead of being a single point. ')
                raise ValueError(msg.format(src_coord.name(), src_coord.shape))

            # Work out which indices apply to the input coord.
            # NOTE: we know how to index the source cube to get a cube with a
            # single point for each coord, but this is very inefficient.
            # So here, we translate cube indexes into *coord* indexes.
            src_coord_dims = cube.coord_dims(src_coord)
            fancy_coord_index_arrays = [list(all_point_indices[:, src_dim])
                                        for src_dim in src_coord_dims]

            # Fill the new coord with all the correct points from the old one.
            new_cube_coord.points = src_coord.points[fancy_coord_index_arrays]
            # NOTE: the new coords do *not* have bounds.

    return new_cube


class UnstructuredNearestNeigbourRegridder(object):
    """
    Encapsulate the operation of :meth:`iris.analysis.trajectory.interpolate`
    with given source and target grids.

    This is the type used by the :class:`~iris.analysis.UnstructuredNearest`
    regridding scheme.

    """
    # TODO: cache the necessary bits of the operation so re-use can actually
    # be more efficient.
    def __init__(self, src_cube, target_grid_cube):
        """
        A nearest-neighbour regridder to perform regridding from the source
        grid to the target grid.

        This can then be applied to any source data with the same structure as
        the original 'src_cube'.

        Args:

        * src_cube:
            The :class:`~iris.cube.Cube` defining the source grid.
            The X and Y coordinates can have any shape, but must be mapped over
            the same cube dimensions.

        * target_grid_cube:
            A :class:`~iris.cube.Cube`, whose X and Y coordinates specify a
            desired target grid.
            The X and Y coordinates must be one-dimensional dimension
            coordinates, mapped to different dimensions.
            All other cube components are ignored.

        Returns:
            regridder : (object)

            A callable object with the interface:
                `result_cube = regridder(data)`

            where `data` is a cube with the same grid as the original
            `src_cube`, that is to be regridded to the `target_grid_cube`.

        .. Note::

            For latitude-longitude coordinates, the nearest-neighbour distances
            are computed on the sphere, otherwise flat Euclidean distances are
            used.

            The source and target X and Y coordinates must all have the same
            coordinate system, which may also be None.
            If any X and Y coordinates are latitudes or longitudes, they *all*
            must be.  Otherwise, the corresponding X and Y coordinates must
            have the same units in the source and grid cubes.

        """
        # Make a copy of the source cube, so we can convert coordinate units.
        src_cube = src_cube.copy()

        # Snapshot the target grid and check it is a "normal" grid.
        tgt_x_coord, tgt_y_coord = snapshot_grid(target_grid_cube)

        # Check that the source has unique X and Y coords over common dims.
        if (not src_cube.coords(axis='x') or not src_cube.coords(axis='y')):
            msg = 'Source cube must have X- and Y-axis coordinates.'
            raise ValueError(msg)
        src_x_coord = src_cube.coord(axis='x')
        src_y_coord = src_cube.coord(axis='y')
        if (src_cube.coord_dims(src_x_coord) !=
                src_cube.coord_dims(src_y_coord)):
            msg = ('Source cube X and Y coordinates must have the same '
                   'cube dimensions.')
            raise ValueError(msg)

        # Record *copies* of the original grid coords, in the desired
        # dimension order.
        # This lets us convert the actual ones in use to units of "degrees".
        self.src_grid_coords = [src_y_coord.copy(), src_x_coord.copy()]
        self.tgt_grid_coords = [tgt_y_coord.copy(), tgt_x_coord.copy()]

        # Check that all XY coords have suitable coordinate systems and units.
        coords_all = [src_x_coord, src_y_coord, tgt_x_coord, tgt_y_coord]
        cs = coords_all[0].coord_system
        if not all(coord.coord_system == cs for coord in coords_all):
            msg = ('Source and target cube X and Y coordinates must all have '
                   'the same coordinate system.')
            raise ValueError(msg)

        # Check *all* X and Y coords are lats+lons, if any are.
        latlons = ['latitude' in coord.name() or 'longitude' in coord.name()
                   for coord in coords_all]
        if any(latlons) and not all(latlons):
            msg = ('If any X and Y coordinates are latitudes/longitudes, '
                   'then they all must be.')
            raise ValueError(msg)

        self.grid_is_latlon = any(latlons)
        if self.grid_is_latlon:
            # Convert all XY coordinates to units of "degrees".
            # N.B. already copied the target grid, so the result matches that.
            for coord in coords_all:
                try:
                    coord.convert_units('degrees')
                except ValueError:
                    msg = ('Coordinate {} has units of {}, which does not '
                           'convert to "degrees".')
                    raise ValueError(msg.format(coord.name(), coord.units))
        else:
            # Check that source and target have the same X and Y units.
            if (src_x_coord.units != tgt_x_coord.units or
                    src_y_coord.units != tgt_y_coord.units):
                msg = ('Source and target cube X and Y coordinates must '
                       'have the same units.')
                raise ValueError(msg)

        # Record the resulting grid shape.
        self.tgt_grid_shape = tgt_y_coord.shape + tgt_x_coord.shape

        # Calculate sample points as 2d arrays, like broadcast (NY,1)*(1,NX).
        x_2d, y_2d = np.meshgrid(tgt_x_coord.points, tgt_y_coord.points)
        # Cast as a "trajectory", to suit the method used.
        self.trajectory = ((tgt_x_coord.name(), x_2d.flatten()),
                           (tgt_y_coord.name(), y_2d.flatten()))

    def __call__(self, src_cube):
        # Check the source cube X and Y coords match the original.
        # Note: for now, this is sufficient to ensure a valid trajectory
        # interpolation, but if in future we save + re-use the cache context
        # for the 'interpolate' call, we may need more checks here.

        # Check the given cube against the original.
        x_cos = src_cube.coords(axis='x')
        y_cos = src_cube.coords(axis='y')
        if (not x_cos or not y_cos or
                y_cos != [self.src_grid_coords[0]] or
                x_cos != [self.src_grid_coords[1]]):
            msg = ('The given cube is not defined on the same source '
                   'grid as this regridder.')
            raise ValueError(msg)

        # Convert source XY coordinates to degrees if required.
        if self.grid_is_latlon:
            src_cube = src_cube.copy()
            src_cube.coord(axis='x').convert_units('degrees')
            src_cube.coord(axis='y').convert_units('degrees')

        # Get the basic interpolated results.
        result_trajectory_cube = interpolate(src_cube, self.trajectory,
                                             method='nearest')

        # Reconstruct this as a cube "like" the source data.
        # TODO: handle all aux-coords, cell measures ??

        # The shape is that of the basic result, minus the trajectory (last)
        # dimension, plus the target grid dimensions.
        target_shape = result_trajectory_cube.shape[:-1] + self.tgt_grid_shape
        data_2d_x_and_y = result_trajectory_cube.data.reshape(target_shape)

        # Make a new result cube with the reshaped data.
        result_cube = iris.cube.Cube(data_2d_x_and_y)
        result_cube.metadata = src_cube.metadata

        # Copy all the coords from the trajectory result.
        i_trajectory_dim = result_trajectory_cube.ndim - 1
        for coord in result_trajectory_cube.dim_coords:
            dims = result_trajectory_cube.coord_dims(coord)
            if i_trajectory_dim not in dims:
                result_cube.add_dim_coord(coord.copy(), dims)
        for coord in result_trajectory_cube.aux_coords:
            dims = result_trajectory_cube.coord_dims(coord)
            if i_trajectory_dim not in dims:
                result_cube.add_aux_coord(coord.copy(), dims)

        # Add the X+Y grid coords from the grid cube, mapped to the new Y and X
        # dimensions, i.e. the last 2.
        for i_dim, coord in enumerate(self.tgt_grid_coords):
            result_cube.add_dim_coord(coord.copy(), i_dim + i_trajectory_dim)

        return result_cube
