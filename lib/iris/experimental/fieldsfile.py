# (C) British Crown Copyright 2014, Met Office
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
High-speed loading of structured FieldsFiles.

"""

from __future__ import (absolute_import, division, print_function)

from iris.coords import DimCoord
from iris.cube import CubeList
from iris.exceptions import TranslationError
from iris.fileformats.ff import FF2PP
from iris.fileformats.pp_rules import (_convert_time_coords,
                                       _convert_vertical_coords,
                                       _convert_scalar_realization_coords,
                                       _convert_scalar_pseudo_level_coords,
                                       _all_other_rules)
from iris.fileformats.rules import ConversionMetadata, Loader, load_cubes
from iris.fileformats.um._fast_load_structured_fields import \
    group_structured_fields


# Seed the preferred order of candidate dimension coordinates.
_HINT_COORDS = ['time', 'forecast_reference_time', 'model_level_number']
_HINTS = {name: i for i, name in zip(range(len(_HINT_COORDS)), _HINT_COORDS)}


def _collations_from_filename(filename):
    fields = iter(FF2PP(filename))
    return group_structured_fields(fields)


def load(filepath):
    """
    Load a structured FieldsFile.

    Args:

    * filepath (string):
        Filepath of the input FieldsFile.

    Returns:
        A :class:`iris.cube.CubeList`.

    """
    loader = Loader(_collations_from_filename, {}, convert_collation, None)
    return CubeList(load_cubes([filepath], None, loader, None))


def _adjust_dims(coords_and_dims, n_dims):
    def adjust(dims):
        if dims is not None:
            dims += n_dims
        return dims
    return [(coord, adjust(dims)) for coord, dims in coords_and_dims]


def _bind_coords(coords_and_dims, dim_coord_dims, dim_coords_and_dims,
                 aux_coords_and_dims):
    key_func = lambda item: _HINTS.get(item[0].name(), len(_HINTS))
    # Target the first DimCoord for a dimension at dim_coords,
    # and target everything else at aux_coords.
    for coord, dims in sorted(coords_and_dims, key=key_func):
        if (isinstance(coord, DimCoord) and dims is not None and
                len(dims) == 1 and dims[0] not in dim_coord_dims):
            dim_coords_and_dims.append((coord, dims))
            dim_coord_dims.add(dims[0])
        else:
            aux_coords_and_dims.append((coord, dims))


def convert_collation(collation):
    """
    Converts a FieldCollation into the corresponding items of Cube
    metadata.

    Args:

    * collation:
        A FieldCollation object.

    Returns:
        A :class:`iris.fileformats.rules.ConversionMetadata` object.

    """
    # For all the scalar conversions all fields in the collation will
    # give the same result, so the choice is arbitrary.
    field = collation.fields[0]

    # All the "other" rules.
    (references, standard_name, long_name, units, attributes, cell_methods,
     dim_coords_and_dims, aux_coords_and_dims) = _all_other_rules(field)

    # Adjust any dimension bindings to account for the extra leading
    # dimensions added by the collation.
    if collation.vector_dims_shape:
        n_collation_dims = len(collation.vector_dims_shape)
        dim_coords_and_dims = _adjust_dims(dim_coords_and_dims,
                                           n_collation_dims)
        aux_coords_and_dims = _adjust_dims(aux_coords_and_dims,
                                           n_collation_dims)

    # "Normal" (non-cross-sectional) time values
    vector_headers = collation.element_arrays_and_dims
    # If the collation doesn't define a vector of values for a
    # particular header then it must be constant over all fields in the
    # collation. In which case it's safe to get the value from any field.
    t1, t1_dims = vector_headers.get('t1', (field.t1, ()))
    t2, t2_dims = vector_headers.get('t2', (field.t2, ()))
    lbft, lbft_dims = vector_headers.get('lbft', (field.lbft, ()))
    coords_and_dims = _convert_time_coords(field.lbcode, field.lbtim,
                                           field.time_unit('hours'),
                                           t1, t2, lbft,
                                           t1_dims, t2_dims, lbft_dims)
    dim_coord_dims = set()
    _bind_coords(coords_and_dims, dim_coord_dims, dim_coords_and_dims,
                 aux_coords_and_dims)

    # "Normal" (non-cross-sectional) vertical levels
    blev, blev_dims = vector_headers.get('blev', (field.blev, ()))
    lblev, lblev_dims = vector_headers.get('lblev', (field.lblev, ()))
    bhlev, bhlev_dims = vector_headers.get('bhlev', (field.bhlev, ()))
    bhrlev, bhrlev_dims = vector_headers.get('bhrlev', (field.bhrlev, ()))
    brsvd1, brsvd1_dims = vector_headers.get('brsvd1', (field.brsvd[0], ()))
    brsvd2, brsvd2_dims = vector_headers.get('brsvd2', (field.brsvd[1], ()))
    brlev, brlev_dims = vector_headers.get('brlev', (field.brlev, ()))
    # Find all the non-trivial dimension values
    dims = set(filter(None, [blev_dims, lblev_dims, bhlev_dims, bhrlev_dims,
                             brsvd1_dims, brsvd2_dims, brlev_dims]))
    if len(dims) > 1:
        raise TranslationError('Unsupported multiple values for vertical '
                               'dimension.')
    if dims:
        v_dims = dims.pop()
        if len(v_dims) > 1:
            raise TranslationError('Unsupported multi-dimension vertical '
                                   'headers.')
    else:
        v_dims = ()
    coords_and_dims, factories = _convert_vertical_coords(field.lbcode,
                                                          field.lbvc,
                                                          blev, lblev,
                                                          field.stash,
                                                          bhlev, bhrlev,
                                                          brsvd1, brsvd2,
                                                          brlev, v_dims)
    _bind_coords(coords_and_dims, dim_coord_dims, dim_coords_and_dims,
                 aux_coords_and_dims)

    # Realization (aka ensemble) (--> scalar coordinates)
    aux_coords_and_dims.extend(_convert_scalar_realization_coords(
        lbrsvd4=field.lbrsvd[3]))

    # Pseudo-level coordinate (--> scalar coordinates)
    aux_coords_and_dims.extend(_convert_scalar_pseudo_level_coords(
        lbuser5=field.lbuser[4]))

    return ConversionMetadata(factories, references, standard_name, long_name,
                              units, attributes, cell_methods,
                              dim_coords_and_dims, aux_coords_and_dims)
