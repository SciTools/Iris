# (C) British Crown Copyright 2019, Met Office
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
"""Unit tests for the `iris.cube.CubeRepresentation` class."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
from html import escape

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris.cube import CubeList
import iris.tests.stock as stock

from iris.experimental.representation import CubeListRepresentation


@tests.skip_data
class Test__instantiation(tests.IrisTest):
    def setUp(self):
        self.cubes = CubeList([stock.simple_3d()])
        self.representer = CubeListRepresentation(self.cubes)

    def test_ids(self):
        self.assertEqual(id(self.cubes), self.representer.cubelist_id)


@tests.skip_data
class Test_make_content(tests.IrisTest):
    def setUp(self):
        self.cubes = CubeList([stock.simple_3d(),
                               stock.lat_lon_cube()])
        self.cubes[0].rename('name & <html>')
        self.representer = CubeListRepresentation(self.cubes)
        self.content = self.representer.make_content()

    def test_repr_len(self):
        self.assertEqual(len(self.cubes), len(self.content))

    def test_summary_lines(self):
        names = [c.name() for c in self.cubes]
        for name, content in zip(names, self.content):
            name = escape(name)
            self.assertIn(name, content)

    def test__cube_name_summary_consistency(self):
        # Just check the first cube in the CubeList.
        single_cube_html = self.content[0]
        first_contents_line = single_cube_html.split('\n')[1]
        # Get a "prettified" cube name, as it should be in the cubelist repr.
        cube_name = self.cubes[0].name()
        pretty_cube_name = cube_name.strip().replace('_', ' ').title()
        pretty_escaped_name = escape(pretty_cube_name)
        self.assertIn(pretty_escaped_name, single_cube_html)


@tests.skip_data
class Test_repr_html(tests.IrisTest):
    def setUp(self):
        self.cubes = CubeList([stock.simple_3d(),
                               stock.lat_lon_cube()])
        self.representer = CubeListRepresentation(self.cubes)

    def test_html_length(self):
        html = self.representer.repr_html()
        n_html_elems = html.count('<button')  # One <button> tag per cube.
        self.assertEqual(len(self.cubes), n_html_elems)


if __name__ == '__main__':
    tests.main()
