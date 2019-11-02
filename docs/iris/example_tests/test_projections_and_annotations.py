# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

from __future__ import absolute_import, division, print_function
from six.moves import filter, input, map, range, zip  # noqa

# Import Iris tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from .extest_util import (
    add_examples_to_path,
    show_replaced_by_check_graphic,
    fail_any_deprecation_warnings,
)


class TestProjectionsAndAnnotations(tests.GraphicsTest):
    """Test the atlantic_profiles example code."""

    def test_projections_and_annotations(self):
        with fail_any_deprecation_warnings():
            with add_examples_to_path():
                import projections_and_annotations
            with show_replaced_by_check_graphic(self):
                projections_and_annotations.main()


if __name__ == "__main__":
    tests.main()
