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

#. N/A


🐛 Bugs Fixed
=============

#. N/A


💣 Incompatible Changes
=======================

#. N/A


🚀 Performance Enhancements
===========================

#. `@fnattino`_ and `@pp-mo`_ prevented cube printout from showing the values of lazy
   scalar coordinates, since this can involve a lengthy computation that must be
   re-computed each time.  (:pull:`5896`)


🔥 Deprecations
===============

#. N/A


🔗 Dependencies
===============

#. N/A


📚 Documentation
================

#. N/A


💼 Internal
===========

#. `@trexfeathers`_ used the `Pull Request Labeler Github action`_ to add the
   ``benchmark_this`` label (:ref:`more info <on_demand_pr_benchmark>`) to
   pull requests that modify ``requirements/locks/*.lock`` files - ensuring
   that we know whether dependency changes will affect performance.
   (:pull:`5763`)


.. comment
    Whatsnew author names (@github name) in alphabetical order. Note that,
    core dev names are automatically included by the common_links.inc:

.. _@fnattino: https://github.com/fnattino


.. comment
    Whatsnew resources in alphabetical order:

.. _Pull Request Labeler GitHub action: https://github.com/actions/labeler
