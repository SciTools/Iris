# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

"""
Plotting support for unstructured meshes with pyvista.

"""

from collections.abc import Iterable
from functools import lru_cache

import cartopy.io.shapereader as shp
from cartopy.io.shapereader import Record
from cf_units import Unit
import numpy as np
import pyvista as pv
from shapely.geometry.multilinestring import MultiLineString
import vtk

from ...config import get_logger


__all__ = [
    "add_coastlines",
    "get_coastlines",
    "plot",
    "to_vtk_mesh",
    "to_xyz",
]

# default to an s2 unit sphere.
RADIUS = 1.0

# VTK cell picker callback hook that requires global context
VTK_PICKER_CALLBACK = dict()

# VTK slider widget callback hook that requires global context
VTK_SLIDER_CALLBACK = dict()


# Configure the logger.
logger = get_logger(__name__, fmt="[%(cls)s.%(funcName)s]")


class vtkPolyDataTransformFilter:
    """
    A VTK transformer that can project PyVista objects from a latitude and
    longitude projection to a given PROJ4 projection.

    .. seealso::

        * https://proj.org/operations/projections/
        * https://vtk.org/doc/nightly/html/classvtkGeoProjection.html

    """

    def __init__(self, projection_specifier=None):
        """
        Create the VTK transform projection filter.

        Args:

        * projection_specifier:
            The target projection. This may simply be the name of the
            projection e.g., ``moll``, ``sinu``. Alternatively, a
            PROJ4 string may be provided e.g., ``+proj=moll +lon_0=90``

        .. note:: Full PROJ4 string support still requires to be implemented.

        """
        # Set up source and target projection.
        sourceProjection = vtk.vtkGeoProjection()
        destinationProjection = vtk.vtkGeoProjection()
        projection_specifier = projection_specifier.strip()

        if projection_specifier.startswith("+"):
            destinationProjection.SetPROJ4String(projection_specifier)
        else:
            destinationProjection.SetName(projection_specifier)

        # Set up transform between source and target.
        transformProjection = vtk.vtkGeoTransform()
        transformProjection.SetSourceProjection(sourceProjection)
        transformProjection.SetDestinationProjection(destinationProjection)

        # Set up transform filter.
        transform_filter = vtk.vtkTransformPolyDataFilter()
        transform_filter.SetTransform(transformProjection)

        self.transform_filter = transform_filter

    def transform(self, mesh):
        """
        Transform the :class:`~pyvista.core.pointset.PolyData` to the
        target projection.

        Args:

        * mesh (PolyData):
            The :class:~pyvista.core.pointset.PolyData` mesh to be transformed.

        """
        self.transform_filter.SetInputData(mesh)
        self.transform_filter.Update()
        output = self.transform_filter.GetOutput()

        # Wrap output of transform as a PyVista object.
        return pv.wrap(output)


def add_coastlines(resolution="110m", projection=None, plotter=None, **kwargs):
    """
    Add the specified Natural Earth coastline geometries to a PyVista plotter
    for rendering.

    Kwargs:

    * resolution (None or str):
        The resolution of the Natural Earth coastlines, which may be either
        ``110m``, ``50m`` or ``10m``. If ``None``, no coastlines are rendered.
        The default is ``110m``.

    * projection (None or str):
        The name of the PROJ4 planar projection used to transform the coastlines
        into a 2D projection coordinate system. If ``None``, the coastline
        geometries are rendered in on a 3D sphere. The default is ``None``.

    * plotter (None or Plotter):
        The :class:`~pyvista.plotting.plotting.Plotter` which renders the scene.
        If ``None``, a plotter object will be created. Default is None.

    * kwargs (dict):
        Additional ``kwargs`` to be passed to PyVista when creating a coastline
        :class:`~pyvista.core.pointset.PolyData`.

    Returns:
        The :class:`~pyvista.plotting.plotting.Plotter`.

    """
    if plotter is None:
        plotter = pv.plotter()

    if not kwargs:
        kwargs = dict(color="black")

    if resolution is not None:
        geocentric = projection is None
        coastlines = get_coastlines(resolution, geocentric=geocentric)

        if projection is not None:
            vtk_projection = vtkPolyDataTransformFilter(projection)
            coastlines = [
                vtk_projection.transform(coastline) for coastline in coastlines
            ]

        for coastline in coastlines:
            plotter.add_mesh(coastline, **kwargs)

    return plotter


@lru_cache
def get_coastlines(resolution="110m", geocentric=False):
    """
    Download and return the collection of Natural Earth coastline geometries.

    The geometries will be transformed appropriately for use with a 2D planar
    projection or a 3D spherical mesh.

    Kwargs:

    * resolution (None or str):
        The resolution of the Natural Earth coastlines, which may be either
        ``110m``, ``50m`` or ``10m``. If ``None``, no coastlines are rendered.
        The default is ``110m``.

    geocentric (bool):
        Convert the coastline latitude and longitude geometries to geocentric
        XYZ coordinates.

    Returns:
        A :class:~pyvista.core.composite.MultiBlock` containing one or more
        :class:`~pyvista.core.pointset.PolyData` coastline geometries.

    """
    # add a "fudge-factor" to ensure coastlines overlay the mesh
    # i.e., a poor mans zorder.
    radius = RADIUS + RADIUS / 1e4

    # load in the shapefiles
    fname = shp.natural_earth(
        resolution=resolution, category="physical", name="coastline"
    )
    reader = shp.Reader(fname)

    dtype = np.float32
    blocks = pv.MultiBlock()
    geoms = []

    def to_pyvista_blocks(records):
        for record in records:
            if isinstance(record, Record):
                geometry = record.geometry
            else:
                geometry = record

            if isinstance(geometry, MultiLineString):
                geoms.extend(list(geometry.geoms))
            else:
                xy = np.array(geometry.coords[:], dtype=dtype)

                if geocentric:
                    # calculate 3d xyz coordinates
                    xr = np.radians(xy[:, 0]).reshape(-1, 1)
                    yr = np.radians(90 - xy[:, 1]).reshape(-1, 1)

                    x = radius * np.sin(yr) * np.cos(xr)
                    y = radius * np.sin(yr) * np.sin(xr)
                    z = radius * np.cos(yr)
                else:
                    # otherwise, calculate xy0 coordinates
                    x = xy[:, 0].reshape(-1, 1)
                    y = xy[:, 1].reshape(-1, 1)
                    z = np.zeros_like(x)

                xyz = np.hstack((x, y, z))
                poly = pv.lines_from_points(xyz, close=False)
                blocks.append(poly)

    to_pyvista_blocks(reader.records())
    to_pyvista_blocks(geoms)

    return blocks


def plot(
    cube,
    projection=None,
    resolution="110m",
    threshold=False,
    invert=False,
    plotter=None,
    **kwargs,
):
    """
    Plot the cube unstructured mesh using PyVista.

    The cube may be either 1D or 2D, where one dimension is the unstructured
    mesh. For 2D cubes, the other dimension is typically a structured vertical or
    layer type dimension, and a slider widget is rendered for the cube structured
    dimension to allow visualisation of the associated unstructured slices.

    Args:

    * cube (Cube):
        The :class:`~iris.cube.Cube` to be rendered.

    Kwargs:

    * projection (None or str):
        The name of the PROJ4 planar projection used to transform the unstructured
        cube mesh into a 2D projection coordinate system. If ``None``, the unstructured
        cube mesh is rendered on a 3D sphere. The default is ``None``.

    * resolution (None or str):
        The resolution of the Natural Earth coastlines, which may be either
        ``110m``, ``50m`` or ``10m``. If ``None``, no coastlines are rendered.
        The default is ``110m``.

    * threshold (None or float or sequence):
        Apply a :class:`~pyvista.core.DataSetFilters.threshold`. Single value or
        (min, max) to be used for the data threshold. If a sequence, then length
        must be 2. If ``None``, the non-NaN data range will be used to remove any
        NaN values. Default is ``None``.

    * invert (bool):
        Invert the nature of the ``threshold``. If ``threshold`` is a single value,
        then when invert is ``True`` cells are kept when their values are below
        parameter ``threshold``. When ``invert`` is ``False`` cells are kept when
        their value is above the ``threshold``. Default is ``False``.

    * plotter (None or Plotter):
        The :class:`~pyvista.plotting.plotting.Plotter` which renders the scene.
        If ``None``, a plotter object will be created. Default is None.

    * kwargs (dict):
        Additional ``kwargs`` to be passed to PyVista when creating
        :class:`~pyvista.core.pointset.PolyData`.

    Returns:
        The :class:`~pyvista.plotting.plotting.Plotter`.

    """
    global VTK_PICKER_CALLBACK
    global VTK_SLIDER_CALLBACK

    if not hasattr(cube, "mesh"):
        emsg = "Require a cube with an unstructured mesh."
        raise TypeError(emsg)

    if plotter is None:
        plotter = pv.Plotter()

    if not kwargs:
        kwargs = dict(
            cmap="balance",
            specular=0.5,
            show_edges=False,
            edge_color="black",
            line_width=0.5,
            scalar_bar_args=dict(nan_annotation=True, shadow=True),
        )

    location = cube.location
    mesh = to_vtk_mesh(cube, projection=projection)

    #
    # threshold the mesh, if appropriate
    #
    if isinstance(threshold, bool) and threshold:
        mesh = mesh.threshold(invert=invert)
    elif not isinstance(threshold, bool):
        mesh = mesh.threshold(threshold, invert=invert)
        if isinstance(threshold, (np.ndarray, Iterable)):
            annotations = {threshold[0]: "Lower", threshold[1]: "Upper"}
            if "annotations" not in kwargs:
                kwargs["annotations"] = annotations

    # add unique cell index values to each cell
    mesh.cell_arrays["cids"] = np.arange(mesh.n_cells, dtype=np.uint32)

    plotter.add_mesh(mesh, scalars=location, **kwargs)

    add_coastlines(
        resolution=resolution, projection=projection, plotter=plotter
    )

    #
    # scalar bar title
    #
    def namify(item):
        name = item.name()
        name = (
            " ".join([part.capitalize() for part in name.split("_")])
            if name
            else "Unknown"
        )
        return name

    if (
        "scalar_bar_args" not in kwargs
        or "title" not in kwargs["scalar_bar_args"]
    ):
        name = namify(cube)
        units = str(cube.units)
        plotter.scalar_bar.SetTitle(f"{name} / {units}")

    #
    # position the camera on the scene
    #
    if projection is not None:
        # planar projection camera position
        cpos = [
            (93959.85410932079, 0.0, 55805210.47284255),
            (93959.85410932079, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
    else:
        # 3D spherical camera position
        cpos = [
            (5.398270655691156, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
        ]

    #
    # text actor for time
    #
    when = None
    coords = cube.coords("time", dimensions=())
    if coords:
        (coord,) = coords
        when = f"Time@{coord.units.num2date(coord.points[0])}"

    coords = cube.coords("forecast_period", dimensions=())
    if coords:
        (coord,) = coords
        if coord.points[0]:
            when = f"{when} ({coord.points[0]} {coord.units})"

    if when:
        plotter.add_text(
            when, shadow=True, position="upper_left", font_size=8, name="when"
        )

    #
    # configure mesh cell picking
    #
    units = (
        "" if cube.units == Unit("1") or cube.units == Unit("") else cube.units
    )

    def picking_callback(mesh):
        global VTK_PICKER_CALLBACK

        if mesh is not None:
            text = ""

            if hasattr(mesh, "cell_arrays"):
                # cache the cell IDs of the cells that have been picked
                VTK_PICKER_CALLBACK["cids"] = np.asarray(
                    mesh.cell_arrays["cids"]
                )
                # get the location values
                values = mesh.cell_arrays[location]
            else:
                # the mesh is the cell values
                values = mesh

            if values.size == 1:
                if not np.isnan(values[0]):
                    name = namify(cube)
                    name = "Cell" if name == "Unknown" else name
                    text = f"{name} = {values[0]:.2f}{units}"
            else:
                min, max, mean = (
                    np.nanmin(values),
                    np.nanmax(values),
                    np.nanmean(values),
                )

                def textify(arg):
                    return f"{arg}" if np.isnan(arg) else f"{arg:.2f}{units}"

                tmin, tmax, tmean = textify(min), textify(max), textify(mean)
                text = f"nCells: {values.size}, Min: {tmin}, Max: {tmax}, Mean: {tmean}"

            if "actor" not in VTK_PICKER_CALLBACK:
                VTK_PICKER_CALLBACK["actor"] = plotter.add_text(
                    text,
                    position="lower_left",
                    font_size=10,
                    shadow=True,
                    name="cell-picking",
                )
            else:
                # lower_left=0, lower_right=1, upper_left=2, upper_right=3,
                # lower_edge=4, right_edge=5, left_edge=6, upper_edge=7
                # see https://vtk.org/doc/nightly/html/classvtkCornerAnnotation.html
                VTK_PICKER_CALLBACK["actor"].SetText(0, text)

    VTK_PICKER_CALLBACK["callback"] = picking_callback
    plotter.enable_cell_picking(
        through=False,
        show_message=False,
        style="points",
        render_points_as_spheres=True,
        line_width=5,
        callback=picking_callback,
    )

    #
    # slider for structured dimension, if appropriate
    #
    if cube.ndim == 2:

        def slider_callback(slider, actor):
            global VTK_SLIDER_CALLBACK
            global VTK_PICKER_CALLBACK

            slider = int(slider)

            # only update if the slider value is different
            if slider != VTK_SLIDER_CALLBACK["value"]:
                sunits = VTK_SLIDER_CALLBACK["sunits"]
                scoord = VTK_SLIDER_CALLBACK["scoord"]
                location = VTK_SLIDER_CALLBACK["location"]
                smesh = VTK_SLIDER_CALLBACK["mesh"]
                if sunits:
                    slabel = f"{sunits.num2date(scoord[slider])}"
                    actor.GetSliderRepresentation().SetLabelFormat(slabel)
                smesh.cell_arrays[location] = smesh.cell_arrays[
                    f"{location}_{slider}"
                ]
                VTK_SLIDER_CALLBACK["value"] = slider

                # refresh the picker, if available
                if "cids" in VTK_PICKER_CALLBACK:
                    # get the caches cell IDs of the picked cells
                    cids = VTK_PICKER_CALLBACK["cids"]
                    # get the associated pick cell values
                    picked = smesh.cell_arrays[location][cids]
                    # deal with the single scalar cell case
                    picked = np.array(picked, ndmin=1)
                    # emulate a pick event to refresh
                    VTK_PICKER_CALLBACK["callback"](picked)

        value = 0
        (udim,) = cube.coord_dims(cube.coord(axis="x", mesh_coords=True))
        sdim = 1 - udim
        scoord = cube.coords(dimensions=(sdim,), dim_coords=True)

        if scoord:
            stitle = namify(scoord[0])
            sunits = scoord[0].units
            scoord = scoord[0].points
        else:
            sunits = stitle = ""
            scoord = np.arange(cube.shape[sdim])

        VTK_SLIDER_CALLBACK["value"] = value
        VTK_SLIDER_CALLBACK["sunits"] = sunits
        VTK_SLIDER_CALLBACK["scoord"] = scoord
        VTK_SLIDER_CALLBACK["location"] = location
        VTK_SLIDER_CALLBACK["mesh"] = mesh

        slabel = f"{sunits.num2date(scoord[value])}" if sunits else ""
        srange = (0, cube.shape[sdim] - 1)

        plotter.add_slider_widget(
            slider_callback,
            srange,
            value=value,
            title=stitle,
            event_type="always",
            pass_widget=True,
            style="modern",
            fmt=slabel,
        )

    plotter.show_axes()
    plotter.camera_position = cpos

    return plotter


def to_vtk_mesh(cube, projection=None, cids=False):
    """
    Create the PyVista representation of the unstructured cube mesh.

    Args:

    * cube (Cube):
        The :class:`~iris.cube.Cube` to be transformed into a
        :class:`~pyvista.core.pointset.PolyData`.

    Kwargs:

    * projection (None or str):
        The name of the PROJ4 planar projection used to transform the unstructured
        cube mesh into a 2D projection coordinate system. If ``None``, the
        unstructured cube mesh is rendered in a 3D. The default is ``None``.

    * cids (bool):
        Specify whether to add a uniquie cell index value to each cell.
        Default is ``False``.

    Returns:
        The :class:`~pyvista.core.pointset.PolyData`.

    """
    if not hasattr(cube, "mesh"):
        emsg = "Require a cube with an unstructured mesh."
        raise TypeError(emsg)

    if cube.ndim not in (1, 2):
        emsg = (
            "Require a 1D or 2D cube with an unstructured mesh, "
            f"got a {cube.ndim}D cube."
        )
        raise ValueError(emsg)

    # replace any masks with NaNs
    data = cube.data
    mask = data.mask
    data = data.data
    if np.any(mask):
        data[mask] = np.nan

    # retrieve the mesh topology and connectivity
    face_node = cube.mesh.face_node_connectivity
    indices = face_node.indices_by_src() - face_node.start_index
    coord_x, coord_y = cube.mesh.node_coords

    # TBD: consider masked coordinate points
    node_x = coord_x.points.data
    node_y = coord_y.points.data

    # determine the unstructured dimension (udim) of the cube.
    udim = cube.mesh_dim()

    if projection is None:
        # convert lat/lon to geocentric xyz
        xyz = to_xyz(node_y, node_x, vstack=False)
    else:
        # convert lat/lon to planar xy0
        # TBD: deal with mesh splitting for +lon_0
        # TBD: deal with full PROJ4 string
        slicer = [slice(None)] * cube.ndim
        node_z = np.zeros_like(node_y)
        # simple approach to [-180..180]
        node_x[node_x > 180] -= 360
        # remove troublesome cells that span seam
        no_wrap = node_x[indices].ptp(axis=-1) < 180
        indices = indices[no_wrap]
        slicer[udim] = no_wrap
        data = data[tuple(slicer)]
        xyz = [node_x, node_y, node_z]

    vertices = np.vstack(xyz).T

    # create connectivity face serialisation i.e., for each quad-mesh face
    # we have (4, C1, C2, C3, C4), where 4 is the number of connectivity
    # indices, followed by the four indices participating in the face.
    N_faces, N_nodes = indices.shape
    faces = np.hstack(
        [
            np.broadcast_to(np.array([N_nodes], np.int8), (N_faces, 1)),
            indices,
        ]
    )

    # create the mesh
    mesh = pv.PolyData(vertices, faces, n_faces=N_faces)

    # add the cube data payload to the mesh as a named "scalar" array
    # based on the location
    if cube.ndim == 1:
        mesh.cell_arrays[cube.location] = data
    else:
        # Determine the structured dimension (sdim) of the cube.
        sdim = 1 - udim

        # add the cache of structured dimension data slices to the mesh
        for dim in range(cube.shape[sdim] - 1, -1, -1):
            slicer = [slice(None)] * cube.ndim
            slicer[sdim] = dim
            mesh.cell_arrays[f"{cube.location}_{dim}"] = data[tuple(slicer)]

        mesh.cell_arrays[cube.location] = data[tuple(slicer)]

    # add cell index (cids) to each cell, if required
    if cids:
        mesh.cell_arrays["cids"] = np.arange(mesh.n_cells, dtype=np.uint32)

    # perform the PROJ4 projection of the mesh, if appropriate
    if projection is not None:
        vtk_projection = vtkPolyDataTransformFilter(projection)
        mesh = vtk_projection.transform(mesh)

    return mesh


def to_xyz(latitudes, longitudes, vstack=True):
    """
    Convert latitudes and longitudes to geocentric XYZ values.

    Args:

    * latitudes (float or sequence)
        The latitude values to be converted.

    * longitudes (float or sequence)
        The longitude values to be converted.

    Kwargs:

    * vstack (bool):
        Specify whether the X, Y and Z values are vertically
        stacked and transposed. Default is ``True``.

    Returns:
        The converted latitudes and longitudes.

    """
    latitudes = np.ravel(latitudes)
    longitudes = np.ravel(longitudes)

    x_rad = np.radians(longitudes)
    y_rad = np.radians(90.0 - latitudes)
    x = RADIUS * np.sin(y_rad) * np.cos(x_rad)
    y = RADIUS * np.sin(y_rad) * np.sin(x_rad)
    z = RADIUS * np.cos(y_rad)
    xyz = [x, y, z]

    if vstack:
        xyz = np.vstack(xyz).T

    return xyz
