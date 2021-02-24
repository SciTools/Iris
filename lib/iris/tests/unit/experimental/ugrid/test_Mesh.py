# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Unit tests for the :class:`iris.experimental.ugrid.Mesh` class."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np

from iris.coords import AuxCoord
from iris.experimental import ugrid

# A collection of minimal coords and connectivities describing an equilateral triangle.
NODE_LON = AuxCoord(
    [0, 2, 1],
    standard_name="longitude",
    long_name="long_name",
    var_name="node_lon",
    attributes={"test": 1},
)
NODE_LAT = AuxCoord([0, 0, 1], standard_name="latitude", var_name="node_lat")
EDGE_LON = AuxCoord(
    [1, 1.5, 0.5], standard_name="longitude", var_name="edge_lon"
)
EDGE_LAT = AuxCoord(
    [0, 0.5, 0.5], standard_name="latitude", var_name="edge_lat"
)
FACE_LON = AuxCoord([0.5], standard_name="longitude", var_name="face_lon")
FACE_LAT = AuxCoord([0.5], standard_name="latitude", var_name="face_lat")

EDGE_NODE = ugrid.Connectivity(
    [[0, 1], [1, 2], [2, 0]],
    cf_role="edge_node_connectivity",
    long_name="long_name",
    var_name="var_name",
    attributes={"test": 1},
)
FACE_NODE = ugrid.Connectivity([[0, 1, 2]], cf_role="face_node_connectivity")
FACE_EDGE = ugrid.Connectivity([[0, 1, 2]], cf_role="face_edge_connectivity")
# Actually meaningless:
FACE_FACE = ugrid.Connectivity([[0, 0, 0]], cf_role="face_face_connectivity")
# Actually meaningless:
EDGE_FACE = ugrid.Connectivity(
    [[0, 0], [0, 0], [0, 0]], cf_role="edge_face_connectivity"
)
BOUNDARY_NODE = ugrid.Connectivity(
    [[0, 1], [1, 2], [2, 0]], cf_role="boundary_node_connectivity"
)


class TestProperties1D(tests.IrisTest):
    # Tests that can re-use a single instance for greater efficiency.

    # Mesh kwargs with topology_dimension=1 and all applicable arguments
    # populated - this tests correct property setting.
    KWARGS = {
        "topology_dimension": 1,
        "node_coords_and_axes": ((NODE_LON, "x"), (NODE_LAT, "y")),
        "connectivities": EDGE_NODE,
        "long_name": "my_topology_mesh",
        "var_name": "mesh",
        "attributes": {"notes": "this is a test"},
        "node_dimension": "NodeDim",
        "edge_dimension": "EdgeDim",
        "edge_coords_and_axes": ((EDGE_LON, "x"), (EDGE_LAT, "y")),
    }

    @classmethod
    def setUpClass(cls):
        cls.mesh = ugrid.Mesh(**cls.KWARGS)

    def test___getstate__(self):
        expected = (
            self.mesh._metadata_manager,
            self.mesh._coord_manager,
            self.mesh._connectivity_manager,
        )
        self.assertEqual(expected, self.mesh.__getstate__())

    def test_all_connectivities(self):
        expected = ugrid.Mesh1DConnectivities(EDGE_NODE)
        self.assertEqual(expected, self.mesh.all_connectivities)

    def test_all_coords(self):
        expected = ugrid.Mesh1DCoords(NODE_LON, NODE_LAT, EDGE_LON, EDGE_LAT)
        self.assertEqual(expected, self.mesh.all_coords)

    def test_boundary_node(self):
        with self.assertRaises(AttributeError):
            _ = self.mesh.boundary_node_connectivity

    def test_connectivities(self):
        # General results. Method intended for inheritance.
        positive_kwargs = (
            {"item": EDGE_NODE},
            {"item": "long_name"},
            {"long_name": "long_name"},
            {"var_name": "var_name"},
            {"attributes": {"test": 1}},
            {"cf_role": "edge_node_connectivity"},
        )

        fake_connectivity = tests.mock.Mock(
            __class__=ugrid.Connectivity, cf_role="fake"
        )
        negative_kwargs = (
            {"item": fake_connectivity},
            {"item": "foo"},
            {"standard_name": "air_temperature"},
            {"long_name": "foo"},
            {"var_name": "foo"},
            {"attributes": {"test": 2}},
            {"cf_role": "foo"},
        )

        func = self.mesh.connectivities
        for kwargs in positive_kwargs:
            self.assertEqual(
                EDGE_NODE, func(**kwargs)["edge_node_connectivity"]
            )
        for kwargs in negative_kwargs:
            self.assertNotIn("edge_node_connectivity", func(**kwargs))

    def test_connectivities_locations(self):
        # topology_dimension-specific results. Method intended to be overridden.
        expected = {EDGE_NODE.cf_role: EDGE_NODE}
        func = self.mesh.connectivities
        self.assertEqual(expected, func(node=True))
        self.assertEqual(expected, func(edge=True))
        with self.assertLogs(ugrid.logger, level="DEBUG") as log:
            self.assertEqual({}, func(face=True))
            self.assertIn("filter for non-existent", log.output[0])

    def test_coords(self):
        # General results. Method intended for inheritance.
        positive_kwargs = (
            {"item": NODE_LON},
            {"item": "longitude"},
            {"standard_name": "longitude"},
            {"long_name": "long_name"},
            {"var_name": "node_lon"},
            {"attributes": {"test": 1}},
        )

        fake_coord = AuxCoord([0])
        negative_kwargs = (
            {"item": fake_coord},
            {"item": "foo"},
            {"standard_name": "air_temperature"},
            {"long_name": "foo"},
            {"var_name": "foo"},
            {"attributes": {"test": 2}},
        )

        func = self.mesh.coords
        for kwargs in positive_kwargs:
            self.assertEqual(NODE_LON, func(**kwargs)["node_x"])
        for kwargs in negative_kwargs:
            self.assertNotIn("node_x", func(**kwargs))

    def test_coords_locations(self):
        # topology_dimension-specific results. Method intended to be overridden.
        all_expected = {
            "node_x": NODE_LON,
            "node_y": NODE_LAT,
            "edge_x": EDGE_LON,
            "edge_y": EDGE_LAT,
        }

        kwargs_expected = (
            ({"axis": "x"}, ("node_x", "edge_x")),
            ({"axis": "y"}, ("node_y", "edge_y")),
            ({"node": True}, ("node_x", "node_y")),
            ({"edge": True}, ("edge_x", "edge_y")),
            ({"node": False}, ("edge_x", "edge_y")),
            ({"edge": False}, ("node_x", "node_y")),
            ({"node": True, "edge": True}, []),
            ({"node": False, "edge": False}, []),
        )

        func = self.mesh.coords
        for kwargs, expected in kwargs_expected:
            expected = {
                k: all_expected[k] for k in expected if k in all_expected
            }
            self.assertEqual(expected, func(**kwargs))

        with self.assertLogs(ugrid.logger, level="DEBUG") as log:
            self.assertEqual({}, func(face=True))
            self.assertIn("filter non-existent", log.output[0])

    def test_edge_dimension(self):
        self.assertEqual(
            self.KWARGS["edge_dimension"], self.mesh.edge_dimension
        )

    def test_edge_coords(self):
        expected = ugrid.MeshEdgeCoords(EDGE_LON, EDGE_LAT)
        self.assertEqual(expected, self.mesh.edge_coords)

    def test_edge_face(self):
        with self.assertRaises(AttributeError):
            _ = self.mesh.edge_face_connectivity

    def test_edge_node(self):
        self.assertEqual(EDGE_NODE, self.mesh.edge_node_connectivity)

    def test_face_coords(self):
        with self.assertRaises(AttributeError):
            _ = self.mesh.face_coords

    def test_face_dimension(self):
        self.assertIsNone(self.mesh.face_dimension)

    def test_face_edge(self):
        with self.assertRaises(AttributeError):
            _ = self.mesh.face_edge_connectivity

    def test_face_face(self):
        with self.assertRaises(AttributeError):
            _ = self.mesh.face_face_connectivity

    def test_face_node(self):
        with self.assertRaises(AttributeError):
            _ = self.mesh.face_node_connectivity

    def test_node_coords(self):
        expected = ugrid.MeshNodeCoords(NODE_LON, NODE_LAT)
        self.assertEqual(expected, self.mesh.node_coords)

    def test_node_dimension(self):
        self.assertEqual(
            self.KWARGS["node_dimension"], self.mesh.node_dimension
        )

    def test_topology_dimension(self):
        self.assertEqual(
            self.KWARGS["topology_dimension"], self.mesh.topology_dimension
        )


class TestProperties2D(TestProperties1D):
    # Additional/specialised tests for topology_dimension=2.
    @classmethod
    def setUpClass(cls):
        cls.KWARGS["topology_dimension"] = 2
        cls.KWARGS["connectivities"] = (
            FACE_NODE,
            EDGE_NODE,
            FACE_EDGE,
            FACE_FACE,
            EDGE_FACE,
            BOUNDARY_NODE,
        )
        cls.KWARGS["face_dimension"] = "FaceDim"
        cls.KWARGS["face_coords_and_axes"] = ((FACE_LON, "x"), (FACE_LAT, "y"))
        super().setUpClass()

    def test_all_connectivities(self):
        expected = ugrid.Mesh2DConnectivities(
            FACE_NODE,
            EDGE_NODE,
            FACE_EDGE,
            FACE_FACE,
            EDGE_FACE,
            BOUNDARY_NODE,
        )
        self.assertEqual(expected, self.mesh.all_connectivities)

    def test_all_coords(self):
        expected = ugrid.Mesh2DCoords(
            NODE_LON, NODE_LAT, EDGE_LON, EDGE_LAT, FACE_LON, FACE_LAT
        )
        self.assertEqual(expected, self.mesh.all_coords)

    def test_boundary_node(self):
        self.assertEqual(BOUNDARY_NODE, self.mesh.boundary_node_connectivity)

    def test_connectivities_locations(self):
        kwargs_expected = (
            ({"node": True}, (EDGE_NODE, FACE_NODE, BOUNDARY_NODE)),
            ({"edge": True}, (EDGE_NODE, FACE_EDGE, EDGE_FACE)),
            ({"face": True}, (FACE_NODE, FACE_EDGE, FACE_FACE, EDGE_FACE)),
            ({"node": False}, (FACE_EDGE, EDGE_FACE, FACE_FACE)),
            ({"edge": False}, (FACE_NODE, BOUNDARY_NODE, FACE_FACE)),
            ({"face": False}, (EDGE_NODE, BOUNDARY_NODE)),
            ({"edge": True, "face": True}, (FACE_EDGE, EDGE_FACE)),
            ({"node": False, "edge": False}, (FACE_FACE,)),
        )
        func = self.mesh.connectivities
        for kwargs, expected in kwargs_expected:
            expected = {c.cf_role: c for c in expected}
            self.assertEqual(expected, func(**kwargs))

    def test_coords_locations(self):
        all_expected = {
            "node_x": NODE_LON,
            "node_y": NODE_LAT,
            "edge_x": EDGE_LON,
            "edge_y": EDGE_LAT,
            "face_x": FACE_LON,
            "face_y": FACE_LAT,
        }

        kwargs_expected = (
            ({"axis": "x"}, ("node_x", "edge_x", "face_x")),
            ({"axis": "y"}, ("node_y", "edge_y", "face_y")),
            ({"node": True}, ("node_x", "node_y")),
            ({"edge": True}, ("edge_x", "edge_y")),
            ({"node": False}, ("edge_x", "edge_y", "face_x", "face_y")),
            ({"edge": False}, ("node_x", "node_y", "face_x", "face_y")),
            ({"face": False}, ("node_x", "node_y", "edge_x", "edge_y")),
            ({"face": True, "edge": True}, []),
            ({"face": False, "edge": False}, ["node_x", "node_y"]),
        )

        func = self.mesh.coords
        for kwargs, expected in kwargs_expected:
            expected = {
                k: all_expected[k] for k in expected if k in all_expected
            }
            self.assertEqual(expected, func(**kwargs))

    def test_edge_face(self):
        self.assertEqual(EDGE_FACE, self.mesh.edge_face_connectivity)

    def test_face_coords(self):
        expected = ugrid.MeshFaceCoords(FACE_LON, FACE_LAT)
        self.assertEqual(expected, self.mesh.face_coords)

    def test_face_dimension(self):
        self.assertEqual(
            self.KWARGS["face_dimension"], self.mesh.face_dimension
        )

    def test_face_edge(self):
        self.assertEqual(FACE_EDGE, self.mesh.face_edge_connectivity)

    def test_face_face(self):
        self.assertEqual(FACE_FACE, self.mesh.face_face_connectivity)

    def test_face_node(self):
        self.assertEqual(FACE_NODE, self.mesh.face_node_connectivity)


class TestOperations1D(tests.IrisTest):
    # Tests that cannot re-use an existing Mesh instance, instead need a new
    # one each time.
    def setUp(self):
        self.mesh = ugrid.Mesh(
            topology_dimension=1,
            node_coords_and_axes=((NODE_LON, "x"), (NODE_LAT, "y")),
            connectivities=EDGE_NODE,
        )

    @staticmethod
    def new_connectivity(connectivity, new_len=False):
        """Provide a new connectivity recognisably different from the original."""
        # NOTE: assumes non-transposed connectivity (src_dim=0).
        if new_len:
            shape = (connectivity.shape[0] + 1, connectivity.shape[1])
        else:
            shape = connectivity.shape
        return connectivity.copy(np.zeros(shape, dtype=int))

    @staticmethod
    def new_coord(coord, new_shape=False):
        """Provide a new coordinate recognisably different from the original."""
        if new_shape:
            shape = tuple([i + 1 for i in coord.shape])
        else:
            shape = coord.shape
        return coord.copy(np.zeros(shape))

    def test___setstate__(self):
        false_metadata_manager = "foo"
        false_coord_manager = "bar"
        false_connectivity_manager = "baz"
        self.mesh.__setstate__(
            (
                false_metadata_manager,
                false_coord_manager,
                false_connectivity_manager,
            )
        )

        self.assertEqual(false_metadata_manager, self.mesh._metadata_manager)
        self.assertEqual(false_coord_manager, self.mesh._coord_manager)
        self.assertEqual(
            false_connectivity_manager, self.mesh._connectivity_manager
        )

    def test_add_connectivities(self):
        # Cannot test ADD - 1D - nothing extra to add beyond minimum.

        for new_len in (False, True):
            # REPLACE connectivities, first with one of the same length, then
            # with one of different length.
            edge_node = self.new_connectivity(EDGE_NODE, new_len)
            self.mesh.add_connectivities(edge_node)
            self.assertEqual(
                ugrid.Mesh1DConnectivities(edge_node),
                self.mesh.all_connectivities,
            )

    def test_add_connectivities_duplicates(self):
        edge_node_one = EDGE_NODE
        edge_node_two = self.new_connectivity(EDGE_NODE)
        self.mesh.add_connectivities(edge_node_one, edge_node_two)
        self.assertEqual(
            edge_node_two,
            self.mesh.edge_node_connectivity,
        )

    def test_add_connectivities_invalid(self):
        face_node = FACE_NODE
        with self.assertLogs(ugrid.logger, level="DEBUG") as log:
            self.mesh.add_connectivities(face_node)
            self.assertIn("Not adding connectivity", log.output[0])

    def test_add_coords(self):
        # ADD coords.
        edge_kwargs = {"edge_x": EDGE_LON, "edge_y": EDGE_LAT}
        self.mesh.add_coords(**edge_kwargs)
        self.assertEqual(
            ugrid.MeshEdgeCoords(**edge_kwargs), self.mesh.edge_coords
        )

        for new_shape in (False, True):
            # REPLACE coords, first with ones of the same shape, then with ones
            # of different shape.
            node_kwargs = {
                "node_x": self.new_coord(NODE_LON, new_shape),
                "node_y": self.new_coord(NODE_LAT, new_shape),
            }
            edge_kwargs = {
                "edge_x": self.new_coord(EDGE_LON, new_shape),
                "edge_y": self.new_coord(EDGE_LAT, new_shape),
            }
            self.mesh.add_coords(**node_kwargs, **edge_kwargs)
            self.assertEqual(
                ugrid.MeshNodeCoords(**node_kwargs), self.mesh.node_coords
            )
            self.assertEqual(
                ugrid.MeshEdgeCoords(**edge_kwargs), self.mesh.edge_coords
            )

    def test_add_coords_face(self):
        self.assertRaises(
            TypeError, self.mesh.add_coords, face_x=FACE_LON, face_y=FACE_LAT
        )

    def test_add_coords_single(self):
        # ADD coord.
        edge_x = EDGE_LON
        expected = ugrid.MeshEdgeCoords(edge_x=edge_x, edge_y=None)
        self.mesh.add_coords(edge_x=edge_x)
        self.assertEqual(expected, self.mesh.edge_coords)

        # REPLACE coords.
        node_x = self.new_coord(NODE_LON)
        edge_x = self.new_coord(EDGE_LON)
        expected_nodes = ugrid.MeshNodeCoords(
            node_x=node_x, node_y=self.mesh.node_coords.node_y
        )
        expected_edges = ugrid.MeshEdgeCoords(edge_x=edge_x, edge_y=None)
        self.mesh.add_coords(node_x=node_x, edge_x=edge_x)
        self.assertEqual(expected_nodes, self.mesh.node_coords)
        self.assertEqual(expected_edges, self.mesh.edge_coords)

        # Attempt to REPLACE coords with those of DIFFERENT SHAPE.
        node_x = self.new_coord(NODE_LON, new_shape=True)
        edge_x = self.new_coord(EDGE_LON, new_shape=True)
        node_kwarg = {"node_x": node_x}
        edge_kwarg = {"edge_x": edge_x}
        both_kwargs = dict(**node_kwarg, **edge_kwarg)
        for kwargs in (node_kwarg, edge_kwarg, both_kwargs):
            self.assertRaisesRegex(
                ValueError,
                ".*requires to have shape.*",
                self.mesh.add_coords,
                **kwargs,
            )

    def test_add_coords_single_face(self):
        self.assertRaises(TypeError, self.mesh.add_coords, face_x=FACE_LON)

    def test_edge_dimension_set(self):
        self.mesh.edge_dimension = "foo"
        self.assertEqual("foo", self.mesh.edge_dimension)

    def test_face_dimension_set(self):
        with self.assertLogs(ugrid.logger, level="DEBUG") as log:
            self.mesh.face_dimension = "foo"
            self.assertIn("Not setting face_dimension", log.output[0])
        self.assertIsNone(self.mesh.face_dimension)

    def test_node_dimension_set(self):
        self.mesh.node_dimension = "foo"
        self.assertEqual("foo", self.mesh.node_dimension)


class TestOperations2D(TestOperations1D):
    # Additional/specialised tests for topology_dimension=2.
    def setUp(self):
        self.mesh = ugrid.Mesh(
            topology_dimension=2,
            node_coords_and_axes=((NODE_LON, "x"), (NODE_LAT, "y")),
            connectivities=(FACE_NODE),
        )

    def test_add_connectivities(self):
        # ADD connectivities.
        kwargs = {
            "edge_node": EDGE_NODE,
            "face_edge": FACE_EDGE,
            "face_face": FACE_FACE,
            "edge_face": EDGE_FACE,
            "boundary_node": BOUNDARY_NODE,
        }
        expected = ugrid.Mesh2DConnectivities(
            face_node=self.mesh.face_node_connectivity, **kwargs
        )
        self.mesh.add_connectivities(*kwargs.values())
        self.assertEqual(expected, self.mesh.all_connectivities)

        # REPLACE connectivities.
        kwargs["face_node"] = FACE_NODE
        for new_len in (False, True):
            # First replace with ones of same length, then with ones of
            # different length.
            kwargs = {
                k: self.new_connectivity(v, new_len) for k, v in kwargs.items()
            }
            self.mesh.add_connectivities(*kwargs.values())
            self.assertEqual(
                ugrid.Mesh2DConnectivities(**kwargs),
                self.mesh.all_connectivities,
            )

    def test_add_connectivities_inconsistent(self):
        # ADD Connectivities.
        self.mesh.add_connectivities(EDGE_NODE)
        face_edge = self.new_connectivity(FACE_EDGE, new_len=True)
        edge_face = self.new_connectivity(EDGE_FACE, new_len=True)
        for args in ([face_edge], [edge_face], [face_edge, edge_face]):
            self.assertRaisesRegex(
                ValueError,
                "inconsistent .* counts.",
                self.mesh.add_connectivities,
                *args,
            )

        # REPLACE Connectivities
        self.mesh.add_connectivities(FACE_EDGE, EDGE_FACE)
        for args in ([face_edge], [edge_face], [face_edge, edge_face]):
            self.assertRaisesRegex(
                ValueError,
                "inconsistent .* counts.",
                self.mesh.add_connectivities,
                *args,
            )

    def test_add_connectivities_invalid(self):
        fake_cf_role = tests.mock.Mock(
            __class__=ugrid.Connectivity, cf_role="foo"
        )
        with self.assertLogs(ugrid.logger, level="DEBUG") as log:
            self.mesh.add_connectivities(fake_cf_role)
            self.assertIn("Not adding connectivity", log.output[0])

    def test_add_coords_face(self):
        # ADD coords.
        kwargs = {"face_x": FACE_LON, "face_y": FACE_LAT}
        self.mesh.add_coords(**kwargs)
        self.assertEqual(ugrid.MeshFaceCoords(**kwargs), self.mesh.face_coords)

        for new_shape in (False, True):
            # REPLACE coords, first with ones of the same shape, then with ones
            # of different shape.
            kwargs = {
                "face_x": self.new_coord(FACE_LON, new_shape),
                "face_y": self.new_coord(FACE_LAT, new_shape),
            }
            self.mesh.add_coords(**kwargs)
            self.assertEqual(
                ugrid.MeshFaceCoords(**kwargs), self.mesh.face_coords
            )

    def test_add_coords_single_face(self):
        # ADD coord.
        face_x = FACE_LON
        expected = ugrid.MeshFaceCoords(face_x=face_x, face_y=None)
        self.mesh.add_coords(face_x=face_x)
        self.assertEqual(expected, self.mesh.face_coords)

        # REPLACE coord.
        face_x = self.new_coord(FACE_LON)
        expected = ugrid.MeshFaceCoords(face_x=face_x, face_y=None)
        self.mesh.add_coords(face_x=face_x)
        self.assertEqual(expected, self.mesh.face_coords)

        # Attempt to REPLACE coord with that of DIFFERENT SHAPE.
        face_x = self.new_coord(FACE_LON, new_shape=True)
        self.assertRaisesRegex(
            ValueError,
            ".*requires to have shape.*",
            self.mesh.add_coords,
            face_x=face_x,
        )

    def test_face_dimension_set(self):
        self.mesh.face_dimension = "foo"
        self.assertEqual("foo", self.mesh.face_dimension)
