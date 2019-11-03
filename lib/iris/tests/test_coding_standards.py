# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

from __future__ import absolute_import, division, print_function
from six.moves import filter, input, map, range, zip  # noqa

# import iris.tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

from datetime import datetime
from fnmatch import fnmatch
from glob import glob
from itertools import chain
import os
import re
import subprocess

import iris


LICENSE_TEMPLATE = """# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details."""

# Guess iris repo directory of Iris - realpath is used to mitigate against
# Python finding the iris package via a symlink.
IRIS_DIR = os.path.realpath(os.path.dirname(iris.__file__))
IRIS_INSTALL_DIR = os.path.dirname(os.path.dirname(IRIS_DIR))
DOCS_DIR = os.path.join(IRIS_INSTALL_DIR, "docs", "iris")
DOCS_DIR = iris.config.get_option("Resources", "doc_dir", default=DOCS_DIR)
exclusion = ["Makefile", "build"]
DOCS_DIRS = glob(os.path.join(DOCS_DIR, "*"))
DOCS_DIRS = [
    DOC_DIR
    for DOC_DIR in DOCS_DIRS
    if os.path.basename(DOC_DIR) not in exclusion
]
# Get a dirpath to the git repository : allow setting with an environment
# variable, so Travis can test for headers in the repo, not the installation.
IRIS_REPO_DIRPATH = os.environ.get("IRIS_REPO_DIR", IRIS_INSTALL_DIR)


class TestLicenseHeaders(tests.IrisTest):
    @staticmethod
    def whatchanged_parse(whatchanged_output):
        """
        Returns a generator of tuples of data parsed from
        "git whatchanged --pretty='TIME:%at". The tuples are of the form
        ``(filename, last_commit_datetime)``

        Sample input::

            ['TIME:1366884020', '',
             ':000000 100644 0000000... 5862ced... A\tlib/iris/cube.py']

        """
        dt = None
        for line in whatchanged_output:
            if not line.strip():
                continue
            elif line.startswith("TIME:"):
                dt = datetime.fromtimestamp(int(line[5:]))
            else:
                # Non blank, non date, line -> must be the lines
                # containing the file info.
                fname = " ".join(line.split("\t")[1:])
                yield fname, dt

    @staticmethod
    def last_change_by_fname():
        """
        Return a dictionary of all the files under git which maps to
        the datetime of their last modification in the git history.

        .. note::

            This function raises a ValueError if the repo root does
            not have a ".git" folder. If git is not installed on the system,
            or cannot be found by subprocess, an IOError may also be raised.

        """
        # Check the ".git" folder exists at the repo dir.
        if not os.path.isdir(os.path.join(IRIS_REPO_DIRPATH, ".git")):
            msg = "{} is not a git repository."
            raise ValueError(msg.format(IRIS_REPO_DIRPATH))

        # Call "git whatchanged" to get the details of all the files and when
        # they were last changed.
        output = subprocess.check_output(
            ["git", "whatchanged", "--pretty=TIME:%ct"], cwd=IRIS_REPO_DIRPATH
        )

        output = output.decode().split("\n")
        res = {}
        for fname, dt in TestLicenseHeaders.whatchanged_parse(output):
            if fname not in res or dt > res[fname]:
                res[fname] = dt

        return res

    def test_license_headers(self):
        exclude_patterns = (
            "setup.py",
            "build/*",
            "dist/*",
            "docs/iris/example_code/*/*.py",
            "docs/iris/src/developers_guide/documenting/*.py",
            "docs/iris/src/sphinxext/gen_gallery.py",
            "docs/iris/src/userguide/plotting_examples/*.py",
            "docs/iris/src/userguide/regridding_plots/*.py",
            "docs/iris/src/developers_guide/gitwash_dumper.py",
            "docs/iris/build/*",
            "lib/iris/analysis/_scipy_interpolate.py",
            "lib/iris/fileformats/_pyke_rules/*",
        )

        try:
            last_change_by_fname = self.last_change_by_fname()
        except ValueError as err:
            # Caught the case where this is not a git repo.
            msg = (
                "Iris installation did not look like a git repo?"
                "\nERR = {}\n\n"
            )
            return self.skipTest(msg.format(str(err)))

        failed = False
        for fname, last_change in sorted(last_change_by_fname.items()):
            full_fname = os.path.join(IRIS_REPO_DIRPATH, fname)
            if (
                full_fname.endswith(".py")
                and os.path.isfile(full_fname)
                and not any(fnmatch(fname, pat) for pat in exclude_patterns)
            ):
                with open(full_fname) as fh:
                    content = fh.read()
                    if not content.startswith(LICENSE_TEMPLATE):
                        print(
                            "The file {} does not start with the required "
                            "license header.".format(fname)
                        )
                        failed = True

        if failed:
            raise ValueError("There were license header failures. See stdout.")


class TestFutureImports(tests.IrisTest):
    excluded = (
        "*/iris/fileformats/_old_pp_packing.py",
        "*/iris/fileformats/_pyke_rules/__init__.py",
        "*/iris/fileformats/_pyke_rules/compiled_krb/__init__.py",
        "*/iris/fileformats/_pyke_rules/compiled_krb/compiled_pyke_files.py",
        "*/iris/fileformats/_pyke_rules/compiled_krb/fc_rules_cf_fc.py",
        "*/docs/iris/example_code/*/*.py",
        "*/docs/iris/src/examples/*/*.py",
        "*/docs/iris/src/developers_guide/documenting/*.py",
    )

    future_imports_pattern = re.compile(
        r"^from __future__ import \(?absolute_import,\s*division,\s*"
        r"print_function(,\s*unicode_literals)?\)?$",
        flags=re.MULTILINE,
    )

    six_import_pattern = re.compile(
        r"^from six.moves import \(?filter, input, map, range, zip\)?  # noqa$",
        flags=re.MULTILINE,
    )

    def test_future_imports(self):
        # Tests that every single Python file includes the appropriate
        # __future__ import to enforce consistent behaviour.
        check_paths = [os.path.dirname(iris.__file__)]
        if DOCS_DIRS:
            check_paths.extend(DOCS_DIRS)

        failed = False
        for dirpath, _, files in chain.from_iterable(
            os.walk(path) for path in check_paths
        ):
            for fname in files:
                full_fname = os.path.join(dirpath, fname)
                if not full_fname.endswith(".py"):
                    continue
                if not os.path.isfile(full_fname):
                    continue
                if any(fnmatch(full_fname, pat) for pat in self.excluded):
                    continue

                with open(full_fname, "r") as fh:
                    content = fh.read()

                    if re.search(self.future_imports_pattern, content) is None:
                        print(
                            "The file {} has no valid __future__ imports "
                            "and has not been excluded from the imports "
                            "test.".format(full_fname)
                        )
                        failed = True

                    if re.search(self.six_import_pattern, content) is None:
                        print(
                            "The file {} has no valid six import "
                            "and has not been excluded from the imports "
                            "test.".format(full_fname)
                        )
                        failed = True

        if failed:
            raise AssertionError(
                "There were Python 3 compatibility import "
                "check failures. See stdout."
            )


if __name__ == "__main__":
    tests.main()
