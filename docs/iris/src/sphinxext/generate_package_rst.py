# (C) British Crown Copyright 2010 - 2014, Met Office
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

import os
import sys
import re
import inspect


document_dict = {
                     # Use autoclass for classes
                     'class': '''
%(object_docstring)s

..

    .. autoclass:: %(object_name)s
        :members:
        :undoc-members:
        :inherited-members:

''',
                     'function': '''
.. autofunction:: %(object_name)s

''',
                     # For everything else, let automodule do some magic...
                     None: '''

.. autodata:: %(object_name)s

'''}


horizontal_sep = """
.. raw:: html

    <p class="hr_p"><a href="#">&uarr;&#32&#32 top &#32&#32&uarr;</a></p>
    <!--

-----------

.. raw:: html

    -->

"""


def lookup_object_type(obj):
    if inspect.isclass(obj):
        return 'class'
    elif inspect.isfunction(obj):
        return 'function'
    else:
        return None


def auto_doc_module(file_path, import_name, root_package, package_toc=None, title=None):
    mod = __import__(import_name)
    mod = sys.modules[import_name]
    elems = dir(mod)

    if '__all__' in elems:
        document_these = [[attr_name, getattr(mod, attr_name)] for attr_name in mod.__all__]
    else:
        document_these = [[attr_name, getattr(mod, attr_name)] for attr_name in elems
                          if not attr_name.startswith('_') and not inspect.ismodule(getattr(mod, attr_name))]
        is_from_this_module = lambda (name, obj), this_module=mod.__name__: hasattr(obj, '__module__') and obj.__module__ == mod.__name__

        document_these = filter(is_from_this_module, document_these)
        sort_order = {'class': 2, 'function': 1}
        # sort them according to sort_order dict
        document_these = sorted(document_these, key=lambda (name, obj): sort_order.get(lookup_object_type(obj), 0))

    lines = []
    for element, obj in document_these:
        obj_content = document_dict[lookup_object_type(obj)] % {'object_name': import_name + '.' + element,
                                                               'object_name_header_line':'+' * len(import_name + '.' + element),
                                                               'object_docstring': inspect.getdoc(obj)}
        lines.append(obj_content)

    lines = horizontal_sep.join(lines)

    module_elements = '\n'.join([' * :py:obj:`%s`' % (element) for element, obj in document_these])

    lines = r'''.. _%(import_name)s:

%(title_underline)s
%(title)s
%(title_underline)s

%(sidebar)s

.. currentmodule:: %(root_package)s

.. automodule:: %(import_name)s

In this module:

%(module_elements)s


''' + lines
    if package_toc:
       sidebar = """
.. sidebar:: Modules in this package

%(package_toc_tree)s

    """ % {'package_toc_tree': package_toc}
    else:
       sidebar = ''

    return lines % {'title': title or import_name,
                    'title_underline': '=' * len(title or import_name),
                    'import_name': import_name, 'root_package': root_package,
                    'sidebar': sidebar, 'module_elements': module_elements}


def auto_doc_package(file_path, import_name, root_package, sub_packages):
    max_depth = 1 if import_name == 'iris' else 2
    package_toc = '\n      '.join(sub_packages)
    package_toc = '''
   .. toctree::
      :maxdepth: %d
      :titlesonly:

      %s


''' % (max_depth, package_toc)

    if '.' in import_name:
        title = None
    else:
        title = import_name.capitalize() + ' reference documentation'

    return auto_doc_module(file_path, import_name, root_package, package_toc=package_toc, title=title)


def auto_package_build(app):

    root_package = app.config.autopackage_name
    if root_package is None:
        raise ValueError('set the autopackage_name variable in the conf.py file')

    if not isinstance(root_package, list):
        raise ValueError("autopackage was expecting a list of packages to document e.g. ['itertools']")

    for package in root_package:
        do_package(package)


def do_package(package_name):

    out_dir = package_name + os.path.sep

    # import the root package. If this fails then an import error will be raised.
    module = __import__(package_name)
    root_package = package_name
    rootdir = os.path.dirname(module.__file__)


    package_folder = []
    module_folders = {}
    for root, subFolders, files in os.walk(rootdir):
        for fname in files:
            name, ext = os.path.splitext(fname)

            # skip some non-relevant files
            if ( fname.startswith('.') or fname.startswith('#') or re.search("^_[^_]", fname) or
                 fname.find('.svn')>=0 or not (ext in ['.py', '.so']) ):
                continue

            rel_path = root_package + os.path.join(root, fname).split(rootdir)[-1]
            mod_folder = root_package + os.path.join(root).split(rootdir)[-1].replace('/','.')

            # only add to package folder list if it contains an __init__ script
            if name == '__init__':
                package_folder.append([mod_folder, rel_path])
            else:
                import_name = mod_folder + '.' + name
                module_folders.setdefault(mod_folder, []).append([import_name, rel_path])
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    for package, package_path in package_folder:
       if '._' in package or 'test' in package:
            continue

       sub_packages = (spackage for spackage, spackage_path in package_folder if spackage != package and spackage.startswith(package))
       paths = [os.path.join(*spackage.rsplit('.', 2)[-2:None])+'.rst' for spackage in sub_packages]
       paths.extend( [os.path.join(os.path.basename(os.path.dirname(path)), os.path.splitext(os.path.basename(path))[0]) for imp_name, path in module_folders.get(package, [])])
       paths.sort()
       doc = auto_doc_package(package_path, package, root_package, paths)

       package_dir = out_dir + package.replace('.', os.path.sep)
       if not os.path.exists(package_dir):
           os.makedirs(out_dir + package.replace('.', os.path.sep))

       out_path = package_dir + '.rst'
       if not os.path.exists(out_path) or doc != ''.join(file(out_path, 'r').readlines()):
            print('creating out of date/non-existant document %s' % out_path)
            file(out_path, 'w').write(doc)

       for import_name, module_path in module_folders.get(package, []):
         doc = auto_doc_module(module_path, import_name, root_package)
         out_path = out_dir + import_name.replace('.', os.path.sep) + '.rst'
         if not os.path.exists(out_path) or doc != ''.join(file(out_path, 'r').readlines()):
            print('creating out of date/non-existant document %s' % out_path)
            file(out_path, 'w').write(doc)


def setup(app):
    app.connect('builder-inited', auto_package_build)
    app.add_config_value('autopackage_name', None, 'env')
