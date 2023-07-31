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

#. N/A


✨ Features
===========

#. `@rcomer`_ rewrote :func:`~iris.util.broadcast_to_shape` so it now handles
   lazy data. (:pull:`5307`)


🐛 Bugs Fixed
=============

#. N/A


💣 Incompatible Changes
=======================

#. N/A


🚀 Performance Enhancements
===========================

#. `@rcomer`_ made :meth:`~iris.cube.Cube.aggregated_by` faster. (:pull:`4970`)
#. `@rsdavies`_ modified the CF compliant standard name for m01s00i023 :issue:`4566`

🔥 Deprecations
===============

#. N/A


🔗 Dependencies
===============

#. N/A


📚 Documentation
================

#. `@tkknight`_ prepared the documentation for dark mode and enable the option
   to use it.  By default the theme will be based on the users system settings,
   defaulting to ``light`` if no system setting is found.  (:pull:`5299`)

#. `@HGWright`_ added a :doc:`/further_topics/dask_best_practices/index`
   section into the user guide, containing advice and use cases to help users
   get the best out of Dask with Iris.


💼 Internal
===========

#. `@pp-mo`_ supported loading and saving netcdf :class:`netCDF4.Dataset` compatible
   objects in place of file-paths, as hooks for a forthcoming
   `"Xarray bridge" <https://github.com/SciTools/iris/issues/4994>`_ facility.
   (:pull:`5214`)

#. `@rcomer`_ updated :func:`~iris.plot.contourf` to avoid using functionality
   that is deprecated in Matplotlib v3.8 (:pull:`5405`)


.. comment
    Whatsnew author names (@github name) in alphabetical order. Note that,
    core dev names are automatically included by the common_links.inc:
.. _@rsdavies: https://github.com/rsdavies



.. comment
    Whatsnew resources in alphabetical order:
