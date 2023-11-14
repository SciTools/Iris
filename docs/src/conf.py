# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

# -*- coding: utf-8 -*-
#
# Iris documentation build configuration file, created by
# sphinx-quickstart on Tue May 25 13:26:23 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.
# ----------------------------------------------------------------------------

import datetime
from importlib.metadata import version as get_version
import ntpath
import os
from pathlib import Path
import re
from subprocess import run
import sys
from urllib.parse import quote
import warnings


# function to write  useful output to stdout, prefixing the source.
def autolog(message):
    print("[{}] {}".format(ntpath.basename(__file__), message))


# -- Check for dev make options to build quicker
skip_api = os.environ.get("SKIP_API")

# -- Are we running on the readthedocs server, if so do some setup -----------
on_rtd = os.environ.get("READTHEDOCS") == "True"

# This is the rtd reference to the version, such as: latest, stable, v3.0.1 etc
rtd_version = os.environ.get("READTHEDOCS_VERSION")
if rtd_version is not None:
    # Make rtd_version safe for use in shields.io badges.
    rtd_version = rtd_version.replace("_", "__")
    rtd_version = rtd_version.replace("-", "--")
    rtd_version = quote(rtd_version)

# branch, tag, external (for pull request builds), or unknown.
rtd_version_type = os.environ.get("READTHEDOCS_VERSION_TYPE")

# For local testing purposes we can force being on RTD and the version
# on_rtd = True           # useful for testing
# rtd_version = "latest"  # useful for testing
# rtd_version = "stable"  # useful for testing
# rtd_version_type = "tag"  # useful for testing
# rtd_version = "my_branch"   # useful for testing

if on_rtd:
    autolog("Build running on READTHEDOCS server")

    # list all the READTHEDOCS environment variables that may be of use
    autolog("Listing all environment variables on the READTHEDOCS server...")

    for item, value in os.environ.items():
        autolog("[READTHEDOCS] {} = {}".format(item, value))

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# custom sphinx extensions
sys.path.append(os.path.abspath("sphinxext"))

# add some sample files from the developers guide..
sys.path.append(os.path.abspath(os.path.join("developers_guide")))

# why isn't the iris path added to it is discoverable too?  We dont need to,
# the sphinext to generate the api rst knows where the source is.  If it
# is added then the travis build will likely fail.

# -- Project information -----------------------------------------------------

project = "Iris"

# define the copyright information for latex builds. Note, for html builds,
# the copyright exists directly inside "_templates/layout.html"
copyright_years = f"2010 - {datetime.datetime.now().year}"
copyright = f"{copyright_years}, Iris Contributors"
author = "Iris Developers"

# The version info for the project you're documenting, acts as replacement for
# |version|, also used in various other places throughout the built documents.
version = get_version("scitools-iris")
release = version
autolog(f"Iris Version = {version}")
autolog(f"Iris Release = {release}")

# -- General configuration ---------------------------------------------------

# Create a variable that can be inserted in the rst "|copyright_years|".
# You can add more variables here if needed.

build_python_version = ".".join([str(i) for i in sys.version_info[:3]])


def _dotv(version):
    result = version
    match = re.match(r"^py(\d+)$", version)
    if match:
        digits = match.group(1)
        if len(digits) > 1:
            result = f"{digits[0]}.{digits[1:]}"
    return result


# Automate the discovery of the python versions tested with CI.
python_support = sorted(
    [fname.stem for fname in Path(".").glob("../../requirements/py*.yml")]
)

if not python_support:
    python_support = "unknown Python versions"
elif len(python_support) == 1:
    python_support = f"Python {_dotv(python_support[0])}"
else:
    rest = ", ".join([_dotv(v) for v in python_support[:-1]])
    last = _dotv(python_support[-1])
    python_support = f"Python {rest} and {last}"

rst_epilog = f"""
.. |copyright_years| replace:: {copyright_years}
.. |python_version| replace:: {build_python_version}
.. |python_support| replace:: {python_support}
.. |iris_version| replace:: v{version}
.. |build_date| replace:: ({datetime.datetime.now().strftime('%d %b %Y')})
"""

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.duration",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.extlinks",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx.ext.napoleon",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
    "matplotlib.sphinxext.mathmpl",
    "matplotlib.sphinxext.plot_directive",
]

if skip_api == "1":
    autolog("Skipping the API docs generation (SKIP_API=1)")
else:
    extensions.extend(["sphinxcontrib.apidoc"])
    extensions.extend(["api_rst_formatting"])

# -- Napoleon extension -------------------------------------------------------
# See https://sphinxcontrib-napoleon.readthedocs.io/en/latest/sphinxcontrib.napoleon.html
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True  # includes dunders in api doc
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = None

# -- copybutton extension -----------------------------------------------------
# See https://sphinx-copybutton.readthedocs.io/en/latest/
copybutton_prompt_text = r">>> |\.\.\. "
copybutton_prompt_is_regexp = True
copybutton_line_continuation_character = "\\"

# sphinx.ext.todo configuration -----------------------------------------------
# See https://www.sphinx-doc.org/en/master/usage/extensions/todo.html
todo_include_todos = True

# api generation configuration
autodoc_member_order = "alphabetical"
autodoc_default_flags = ["show-inheritance"]

# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints
autodoc_typehints = "none"
autosummary_generate = True
autosummary_imported_members = True
autopackage_name = ["iris"]
autoclass_content = "both"
modindex_common_prefix = ["iris"]

# -- apidoc extension ---------------------------------------------------------
# See https://github.com/sphinx-contrib/apidoc
source_code_root = (Path(__file__).parents[2]).absolute()
module_dir = source_code_root / "lib"
apidoc_module_dir = str(module_dir)
apidoc_output_dir = str(Path(__file__).parent / "generated/api")
apidoc_toc_file = False

apidoc_excluded_paths = [
    str(module_dir / "iris/tests"),
    str(module_dir / "iris/experimental/raster.*"),  # gdal conflicts
]

apidoc_module_first = True
apidoc_separate_modules = True
apidoc_extra_args = []

autolog(f"[sphinx-apidoc] source_code_root = {source_code_root}")
autolog(f"[sphinx-apidoc] apidoc_excluded_paths = {apidoc_excluded_paths}")
autolog(f"[sphinx-apidoc] apidoc_output_dir = {apidoc_output_dir}")

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# -- intersphinx extension ----------------------------------------------------
# See https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
intersphinx_mapping = {
    "cartopy": ("https://scitools.org.uk/cartopy/docs/latest/", None),
    "dask": ("https://docs.dask.org/en/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "python": ("https://docs.python.org/3/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "dask": ("https://docs.dask.org/en/stable/", None),
}

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# -- plot_directive extension -------------------------------------------------
# See https://matplotlib.org/stable/api/sphinxext_plot_directive_api.html#options
plot_formats = [
    ("png", 100),
]

# -- Extlinks extension -------------------------------------------------------
# See https://www.sphinx-doc.org/en/master/usage/extensions/extlinks.html

extlinks = {
    "issue": ("https://github.com/SciTools/iris/issues/%s", "Issue #%s"),
    "pull": ("https://github.com/SciTools/iris/pull/%s", "PR #%s"),
    "discussion": (
        "https://github.com/SciTools/iris/discussions/%s",
        "Discussion #%s",
    ),
}

# -- Doctest ("make doctest")--------------------------------------------------

doctest_global_setup = "import iris"

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_favicon = "_static/iris-logo.svg"
html_theme = "pydata_sphinx_theme"

# See https://pydata-sphinx-theme.readthedocs.io/en/latest/user_guide/configuring.html#configure-the-search-bar-position
html_sidebars = {
    "**": [
        "custom_sidebar_logo_version",
        "search-field",
        "sidebar-nav-bs",
        "sidebar-ethical-ads",
    ]
}

# See https://pydata-sphinx-theme.readthedocs.io/en/latest/user_guide/configuring.html
html_theme_options = {
    "footer_start": ["copyright", "sphinx-version"],
    "footer_end": ["custom_footer"],
    "collapse_navigation": True,
    "navigation_depth": 3,
    "show_prev_next": True,
    "navbar_align": "content",
    # removes the search box from the top bar
    "navbar_persistent": [],
    # TODO: review if 6 links is too crowded.
    "header_links_before_dropdown": 6,
    "github_url": "https://github.com/SciTools/iris",
    "twitter_url": "https://twitter.com/scitools_iris",
    # icons available: https://fontawesome.com/v5.15/icons?d=gallery&m=free
    "icon_links": [
        {
            "name": "GitHub Discussions",
            "url": "https://github.com/SciTools/iris/discussions",
            "icon": "far fa-comments",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/scitools-iris/",
            "icon": "fas fa-box",
        },
        {
            "name": "Conda",
            "url": "https://anaconda.org/conda-forge/iris",
            "icon": "fas fa-boxes",
        },
    ],
    "use_edit_page_button": True,
    "show_toc_level": 1,
    # Omit `theme-switcher` from navbar_end below to disable it
    # Info: https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/light-dark.html#configure-default-theme-mode
    # "navbar_end": ["navbar-icon-links"],
    # https://pydata-sphinx-theme.readthedocs.io/en/v0.11.0/user_guide/branding.html#different-logos-for-light-and-dark-mode
    "logo": {
        "image_light": "_static/iris-logo-title.svg",
        "image_dark": "_static/iris-logo-title-dark.svg",
    },
}

# if we are building via Read The Docs and it is the latest (not stable)
if on_rtd and rtd_version == "latest":
    html_theme_options[
        "announcement"
    ] = f"""
        You are viewing the <b>latest</b> unreleased documentation
        <strong>{version}</strong>. You can switch to a
        <a href="https://scitools-iris.readthedocs.io/en/stable/">stable</a>
        version."""

rev_parse = run(["git", "rev-parse", "--short", "HEAD"], capture_output=True)
commit_sha = rev_parse.stdout.decode().strip()

html_context = {
    # pydata_theme
    "github_repo": "iris",
    "github_user": "scitools",
    "github_version": "main",
    "doc_path": "docs/src",
    # default theme.  Also disabled the button in the html_theme_options.
    # Info: https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/light-dark.html#configure-default-theme-mode
    "default_mode": "auto",
    # custom
    "on_rtd": on_rtd,
    "rtd_version": rtd_version,
    "rtd_version_type": rtd_version_type,
    "version": version,
    "copyright_years": copyright_years,
    "python_version": build_python_version,
    "commit_sha": commit_sha,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_style = "theme_override.css"

# this allows for using datatables: https://datatables.net/.
# the version can be manually upgraded by changing the urls below.
html_css_files = [
    "https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css",
]

html_js_files = [
    "https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js",
]

# url link checker.  Some links work but report as broken, lets ignore them.
# See https://www.sphinx-doc.org/en/1.2/config.html#options-for-the-linkcheck-builder
linkcheck_ignore = [
    "http://catalogue.ceda.ac.uk/uuid/82adec1f896af6169112d09cc1174499",
    "http://cfconventions.org",
    "http://code.google.com/p/msysgit/downloads/list",
    "http://effbot.org",
    "https://help.github.com",
    "https://docs.github.com",
    "https://github.com",
    "http://www.personal.psu.edu/cab38/ColorBrewer/ColorBrewer_updates.html",
    "http://scitools.github.com/cartopy",
    "http://www.wmo.int/pages/prog/www/DPFS/documents/485_Vol_I_en_colour.pdf",
    "https://software.ac.uk/how-cite-software",
    "http://www.esrl.noaa.gov/psd/data/gridded/conventions/cdc_netcdf_standard.shtml",
    "http://www.nationalarchives.gov.uk/doc/open-government-licence",
    "https://www.metoffice.gov.uk/",
    "https://biggus.readthedocs.io/",
    "https://stickler-ci.com/",
]

# list of sources to exclude from the build.
exclude_patterns = []

# -- sphinx-gallery config ----------------------------------------------------
# See https://sphinx-gallery.github.io/stable/configuration.html

sphinx_gallery_conf = {
    # path to your example scripts
    "examples_dirs": ["../gallery_code"],
    # path to where to save gallery generated output
    "gallery_dirs": ["generated/gallery"],
    # filename pattern for the files in the gallery
    "filename_pattern": "/plot_",
    # filename pattern to ignore in the gallery
    "ignore_pattern": r"__init__\.py",
    # force gallery building, unless overridden (see src/Makefile)
    "plot_gallery": "'True'",
    # force re-registering of nc-time-axis with matplotlib for each example,
    # required for sphinx-gallery>=0.11.0
    "reset_modules": (
        lambda gallery_conf, fname: sys.modules.pop("nc_time_axis", None),
    ),
}

# -----------------------------------------------------------------------------
# Remove warnings
warnings.filterwarnings("ignore")

# -- numfig options (built-in) ------------------------------------------------
# Enable numfig.
numfig = True

numfig_format = {
    "code-block": "Example %s",
    "figure": "Figure %s",
    "section": "Section %s",
    "table": "Table %s",
}
