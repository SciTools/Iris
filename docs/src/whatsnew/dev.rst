.. include:: ../common_links.inc

|iris_version| |build_date| [unreleased]
****************************************

This document explains the changes made to Iris for this release
(:doc:`View all changes <index>`.)


.. dropdown:: :opticon:`report` |iris_version| Release Highlights
   :container: + shadow
   :title: text-primary text-center font-weight-bold
   :body: bg-light
   :animate: fade-in
   :open:

   The highlights for this minor release of Iris include:

   * N/A

   And finally, get in touch with us on :issue:`GitHub<new/choose>` if you have
   any issues or feature requests for improving Iris. Enjoy!


📢 Announcements
================

#. N/A


✨ Features
===========

#. `@wjbenfold`_ added support for ``false_easting`` and ``false_northing`` to
   :class:`~iris.coord_system.Mercator`. (:issue:`3107`, :pull:`4524`)

#. `@rcomer`_ implemented lazy aggregation for the
   :obj:`iris.analysis.PERCENTILE` aggregator. (:pull:`3901`)

#. `@pp-mo`_ fixed cube arithmetic operation for cubes with meshes.
   (:issue:`4454`, :pull:`4651`)


🐛 Bugs Fixed
=============

#. `@rcomer`_ reverted part of the change from :pull:`3906` so that
   :func:`iris.plot.plot` no longer defaults to placing a "Y" coordinate (e.g.
   latitude) on the y-axis of the plot. (:issue:`4493`, :pull:`4601`)

#. `@rcomer`_ enabled passing of scalar objects to :func:`~iris.plot.plot` and
   :func:`~iris.plot.scatter`. (:pull:`4616`)

#. `@rcomer`_ fixed :meth:`~iris.cube.Cube.aggregated_by` with `mdtol` for 1D
   cubes where an aggregated section is entirely masked, reported at
   :issue:`3190`.  (:pull:`4246`)

#. `@rcomer`_ ensured that a :class:`matplotlib.axes.Axes`'s position is preserved
   when Iris replaces it with a :class:`cartopy.mpl.geoaxes.GeoAxes`, fixing
   :issue:`1157`.  (:pull:`4273`)
   
#. `@rcomer`_ fixed :meth:`~iris.coords.Coord.nearest_neighbour_index` for edge
   cases where the requested point is float and the coordinate has integer
   bounds, reported at :issue:`2969`. (:pull:`4245`)

#. `@rcomer`_ modified bounds setting on :obj:`~iris.coords.DimCoord` instances
   so that the order of the cell bounds is automatically reversed
   to match the coordinate's direction if necessary.  This is consistent with
   the `Bounds for 1-D coordinate variables` subsection of the `Cell Boundaries`_
   section of the CF Conventions and ensures that contiguity is preserved if a
   coordinate's direction is reversed. (:issue:`3249`, :issue:`423`,
   :issue:`4078`, :issue:`3756`, :pull:`4466`)


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

#. `@rcomer`_ introduced the ``nc-time-axis >=1.4`` minimum pin, reflecting that
   we no longer use the deprecated :class:`nc_time_axis.CalendarDateTime`
   when plotting against time coordinates. (:pull:`4584`)


📚 Documentation
================

#. `@tkknight`_ added a page to show the issues that have been voted for.  See
   :ref:`voted_issues`. (:issue:`3307`, :pull:`4617`)
#. `@wjbenfold`_ added a note about fixing proxy URLs in lockfiles generated
   because dependencies have changed. (:pull:`4666`)
#. `@lbdreyer`_ moved most of the User Guide's :class:`iris.Constraint` examples
   from :doc:`loading_iris_cubes` to :ref:`cube_extraction` and added an
   example of constraining on bounded time. (:pull:`4656`)


💼 Internal
===========

#. `@trexfeathers`_ and `@pp-mo`_ finished implementing a mature benchmarking
   infrastructure (see :ref:`contributing.benchmarks`), building on 2 hard
   years of lessons learned 🎉. (:pull:`4477`, :pull:`4562`, :pull:`4571`,
   :pull:`4583`, :pull:`4621`)
#. `@wjbenfold`_ used the aforementioned benchmarking infrastructure to
   introduce deep (large 3rd dimension) loading and realisation benchmarks.
   (:pull:`4654`)
#. `@wjbenfold`_ made :func:`iris.tests.stock.simple_1d` respect the
   ``with_bounds`` argument. (:pull:`4658`)


.. comment
    Whatsnew author names (@github name) in alphabetical order. Note that,
    core dev names are automatically included by the common_links.inc:




.. comment
    Whatsnew resources in alphabetical order:

.. _Cell Boundaries: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.9/cf-conventions.html#cell-boundaries
