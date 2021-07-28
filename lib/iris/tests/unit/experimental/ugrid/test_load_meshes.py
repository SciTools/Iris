# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Unit tests for the :func:`iris.experimental.ugrid.load_meshes` function.

"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests  # isort:skip

from pathlib import Path
from shutil import rmtree
from subprocess import check_call
import tempfile
from uuid import uuid4

from iris.experimental.ugrid import PARSE_UGRID_ON_LOAD, load_meshes, logger


def setUpModule():
    global TMP_DIR
    TMP_DIR = Path(tempfile.mkdtemp())


def tearDownModule():
    if TMP_DIR is not None:
        rmtree(TMP_DIR)


def cdl_to_nc(cdl):
    cdl_path = TMP_DIR / "tst.cdl"
    nc_path = TMP_DIR / f"{uuid4()}.nc"
    # Write CDL string into a temporary CDL file.
    with open(cdl_path, "w") as f_out:
        f_out.write(cdl)
    # Use ncgen to convert this into an actual (temporary) netCDF file.
    command = "ncgen -o {} {}".format(nc_path, cdl_path)
    check_call(command, shell=True)
    return str(nc_path)


class Tests(tests.IrisTest):
    def setUp(self):
        self.ref_cdl = """
            netcdf mesh_test {
                dimensions:
                    node = 3 ;
                    face = 1 ;
                    vertex = 3 ;
                    levels = 2 ;
                variables:
                    int mesh ;
                        mesh:cf_role = "mesh_topology" ;
                        mesh:topology_dimension = 2 ;
                        mesh:node_coordinates = "node_x node_y" ;
                        mesh:face_coordinates = "face_x face_y" ;
                        mesh:face_node_connectivity = "face_nodes" ;
                    float node_x(node) ;
                        node_x:standard_name = "longitude" ;
                    float node_y(node) ;
                        node_y:standard_name = "latitude" ;
                    float face_x(face) ;
                        face_x:standard_name = "longitude" ;
                    float face_y(face) ;
                        face_y:standard_name = "latitude" ;
                    int face_nodes(face, vertex) ;
                        face_nodes:cf_role = "face_node_connectivity" ;
                        face_nodes:start_index = 0 ;
                    int levels(levels) ;
                    float node_data(levels, node) ;
                        node_data:coordinates = "node_x node_y" ;
                        node_data:location = "node" ;
                        node_data:mesh = "mesh" ;
                    float face_data(levels, face) ;
                        face_data:coordinates = "face_x face_y" ;
                        face_data:location = "face" ;
                        face_data:mesh = "mesh" ;
                data:
                    mesh = 0;
                    node_x = 0., 2., 1.;
                    node_y = 0., 0., 1.;
                    face_x = 0.5;
                    face_y = 0.5;
                    face_nodes = 0, 1, 2;
                    levels = 1, 2;
                    node_data = 0., 0., 0.;
                    face_data = 0.;
                }
            """
        self.nc_path = cdl_to_nc(self.ref_cdl)

    def test_with_data(self):
        nc_path = cdl_to_nc(self.ref_cdl)
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes(nc_path)

        files = list(meshes.keys())
        self.assertEqual(1, len(files))
        file_meshes = meshes[files[0]]
        self.assertEqual(1, len(file_meshes))
        mesh = file_meshes[0]
        self.assertEqual("mesh", mesh.var_name)

    def test_no_data(self):
        cdl_lines = self.ref_cdl.split("\n")
        cdl_lines = filter(
            lambda line: ':mesh = "mesh"' not in line, cdl_lines
        )
        ref_cdl = "\n".join(cdl_lines)

        nc_path = cdl_to_nc(ref_cdl)
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes(nc_path)

        files = list(meshes.keys())
        self.assertEqual(1, len(files))
        file_meshes = meshes[files[0]]
        self.assertEqual(1, len(file_meshes))
        mesh = file_meshes[0]
        self.assertEqual("mesh", mesh.var_name)

    def test_var_name(self):
        nc_path = cdl_to_nc(self.ref_cdl)
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes(nc_path, "some_other_mesh")
        self.assertDictEqual({}, meshes)

    def test_multi_files(self):
        files_count = 3
        nc_paths = [cdl_to_nc(self.ref_cdl) for _ in range(files_count)]
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes(nc_paths)
        self.assertEqual(files_count, len(meshes))

    def test_multi_meshes(self):
        cdl_extra = """
                    int mesh2 ;
                        mesh2:cf_role = "mesh_topology" ;
                        mesh2:topology_dimension = 2 ;
                        mesh2:node_coordinates = "node_x node_y" ;
                        mesh2:face_coordinates = "face_x face_y" ;
                        mesh2:face_node_connectivity = "face_nodes" ;
            """
        vars_string = "variables:"
        vars_start = self.ref_cdl.index(vars_string) + len(vars_string)
        ref_cdl = (
            self.ref_cdl[:vars_start] + cdl_extra + self.ref_cdl[vars_start:]
        )

        nc_path = cdl_to_nc(ref_cdl)
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes(nc_path)

        files = list(meshes.keys())
        self.assertEqual(1, len(files))
        file_meshes = meshes[files[0]]
        self.assertEqual(2, len(file_meshes))
        mesh_names = [mesh.var_name for mesh in file_meshes]
        self.assertIn("mesh", mesh_names)
        self.assertIn("mesh2", mesh_names)

    def test_no_parsing(self):
        nc_path = cdl_to_nc(self.ref_cdl)
        with self.assertRaisesRegex(
            ValueError, ".*Must be True to enable mesh loading."
        ):
            _ = load_meshes(nc_path)

    def test_invalid_scheme(self):
        with self.assertRaisesRegex(
            ValueError, "Iris cannot handle the URI scheme:.*"
        ):
            with PARSE_UGRID_ON_LOAD.context():
                _ = load_meshes("foo://bar")

    def test_http(self):
        # Are we OK to rely on a 3rd party URL?
        #  Should we instead be hosting a UGRID file over OpenDAP for testing?
        #  Fairly slow.
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes(
                "http://amb6400b.stccmop.org:8080/thredds/dodsC/model_data/forecast"
            )

        files = list(meshes.keys())
        self.assertEqual(1, len(files))
        file_meshes = meshes[files[0]]
        self.assertEqual(1, len(file_meshes))
        mesh = file_meshes[0]
        self.assertEqual("Mesh", mesh.var_name)

    def test_mixed_sources(self):
        URL = "http://amb6400b.stccmop.org:8080/thredds/dodsC/model_data/forecast"
        file = cdl_to_nc(self.ref_cdl)
        glob = f"{TMP_DIR}/*.nc"
        with PARSE_UGRID_ON_LOAD.context():
            meshes = load_meshes([URL, glob])
        for source in (URL, file):
            self.assertIn(source, meshes)

    @tests.skip_data
    def test_non_nc(self):
        log_regex = r"Ignoring non-NetCDF file:.*"
        with self.assertLogs(logger, level="INFO", msg_regex=log_regex):
            with PARSE_UGRID_ON_LOAD.context():
                meshes = load_meshes(
                    tests.get_data_path(["PP", "simple_pp", "global.pp"])
                )
        self.assertDictEqual({}, meshes)
