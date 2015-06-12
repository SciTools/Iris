# (C) British Crown Copyright 2013 - 2015, Met Office
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

from __future__ import (absolute_import, division, print_function)

import six

# Import Iris tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from . import extest_util

with extest_util.add_examples_to_path():
    import atlantic_profiles


class TestAtlanticProfiles(tests.GraphicsTest):
    """Test the atlantic_profiles example code."""
    def test_atlantic_profiles(self):
        with extest_util.show_replaced_by_check_graphic(self, tol=14.0):
            atlantic_profiles.main()


if __name__ == '__main__':
    tests.main()
