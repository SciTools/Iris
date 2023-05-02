.. include:: ../common_links.inc

|iris_version| |build_date| [unreleased]
****************************************

This document explains the changes made to Iris for this release
(:doc:`View all changes <index>`.)


.. dropdown:: |iris_version| Release Highlights
   :color: primary
   :icon: info
   :animate: fade-in
   :open:

   The highlights for this major/minor release of Iris include:

   * N/A

   And finally, get in touch with us on :issue:`GitHub<new/choose>` if you have
   any issues or feature requests for improving Iris. Enjoy!


📢 Announcements
================

#. `@bjlittle`_ added the community `Contributor Covenant`_ code of conduct.
   (:pull:`5291`)


✨ Features
===========

#. `@pp-mo`_ and  `@lbdreyer`_ supported delayed saving of lazy data, when writing to
   the netCDF file format.  See : :ref:`delayed netCDF saves <delayed_netcdf_save>`.
   Also with significant input from `@fnattino`_.
   (:pull:`5191`)

#. `@rcomer`_ tweaked binary operations so that dask arrays may safely be passed
   to arithmetic operations and :func:`~iris.util.mask_cube`. (:pull:`4929`)


🐛 Bugs Fixed
=============

#. `@rcomer`_ enabled automatic replacement of a Matplotlib
   :class:`~matplotlib.axes.Axes` with a Cartopy
   :class:`~cartopy.mpl.geoaxes.GeoAxes` when the ``Axes`` is on a
   :class:`~matplotlib.figure.SubFigure`. (:issue:`5282`, :pull:`5288`)


💣 Incompatible Changes
=======================

#. N/A


🚀 Performance Enhancements
===========================

#. N/A


🔥 Deprecations
===============

#. N/A


🔗 Dependencies
===============

#. `@rcomer`_ and `@bjlittle`_ (reviewer) added testing support for python
   3.11. (:pull:`5226`)

#. `@rcomer`_ dropped support for python 3.8, in accordance with the NEP29_
   recommendations (:pull:`5226`)

#. `@trexfeathers`_ introduced the ``libnetcdf !=4.9.1`` and ``numpy !=1.24.3``
   pins (:pull:`5274`)


📚 Documentation
================

#. `@tkknight`_ migrated to `sphinx-design`_ over the legacy `sphinx-panels`_.
   (:pull:`5127`)

#. `@tkknight`_ updated the ``make`` target for ``help`` and added
   ``livehtml`` to auto generate the documentation when changes are detected
   during development. (:pull:`5258`)

#. `@tkknight`_ updated the :ref:`installing_from_source` instructions to use
   ``pip``.  (:pull:`5273`)

#. `@tkknight`_ removed the legacy custom sphinx extensions that generate the
   API documentation.  Instead use a less complex approach via
   `sphinx-apidoc`_. (:pull:`5264`)

#. `@trexfeathers`_ re-wrote the :ref:`iris_development_releases` documentation
   for clarity, and wrote a step-by-step
   :doc:`/developers_guide/release_do_nothing` for the release process.
   (:pull:`5134`)

#. `@trexfeathers`_ and `@tkknight`_ added a dark-mode friendly logo.
   (:pull:`5278`)


💼 Internal
===========

#. `@bjlittle`_ added the `codespell`_ `pre-commit`_ ``git-hook`` to automate
   spell checking within the code-base. (:pull:`5186`)

#. `@bjlittle`_ and `@trexfeathers`_ (reviewer) added a `check-manifest`_
   GitHub Action and `pre-commit`_ ``git-hook`` to automate verification
   of assets bundled within a ``sdist`` and binary ``wheel`` of our
   `scitools-iris`_ PyPI package. (:pull:`5259`)

#. `@rcomer`_ removed a now redundant copying workaround from Resolve testing.
   (:pull:`5267`)

#. `@bjlittle`_ and `@trexfeathers`_ (reviewer) migrated ``setup.cfg`` to
   ``pyproject.toml``, as motivated by `PEP-0621`_. (:pull:`5262`)

#. `@bjlittle`_ adopted `pypa/build`_ recommended best practice to build a
   binary ``wheel`` from the ``sdist``. (:pull:`5266`)

#. `@trexfeathers`_ enabled on-demand benchmarking of Pull Requests; see
   :ref:`here <on_demand_pr_benchmark>`. (:pull:`5286`)


.. comment
    Whatsnew author names (@github name) in alphabetical order. Note that,
    core dev names are automatically included by the common_links.inc:

.. _@fnattino: https://github.com/fnattino


.. comment
    Whatsnew resources in alphabetical order:

.. _sphinx-panels: https://github.com/executablebooks/sphinx-panels
.. _sphinx-design: https://github.com/executablebooks/sphinx-design
.. _check-manifest: https://github.com/mgedmin/check-manifest
.. _PEP-0621: https://peps.python.org/pep-0621/
.. _pypa/build: https://pypa-build.readthedocs.io/en/stable/
.. _NEP29: https://numpy.org/neps/nep-0029-deprecation_policy.html
.. _Contributor Covenant: https://www.contributor-covenant.org/version/2/1/code_of_conduct/