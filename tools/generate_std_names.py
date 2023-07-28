# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
A script to convert the standard names information from the provided XML
file into a Python dictionary format.

Takes two or three arguments: the first is the XML file to process and the second
is the name of the file to write the Python dictionary file into. The optional
third argument, '--descr', includes the standard name descriptions in the file.

By default, Iris will use the source XML file:
    etc/cf-standard-name-table.xml
as obtained from:
    http://cfconventions.org/standard-names.html
    E.G. http://cfconventions.org/Data/cf-standard-names/78/src/cf-standard-name-table.xml
    - N.B. no fixed 'latest' url is provided.

"""

import argparse
import xml.etree.ElementTree as ET


STD_NAME_TABLE_FILE_TEMPLATE = '''
# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
This file is automatically generated. Do not edit this file by hand.

The file contains the following elements, formatted as python code:
 * A few variablles used internally in the standard name processing.
   These beginn with an underscore.
 * Information on the source standard name table version.
 * A dictionary of standard value names that are mapped
   to another dictionary of other standard name attributes.
   Currently only the `canonical_unit` exists in these attribute
   dictionaries.
 * A dictionary of aliased standard names that are mapped to the
   current standad name.
 * Optionally, a dictionary of standard names mapped to their descriptions.

The file will be generated during a standard build/installation::

    python setup.py build
    python setup.py install

Also, the file can be re-generated in the source distribution via::

    python setup.py std_names

Or for more control (e.g. to use an alternative XML file) via::

    python tools/generate_std_names.py XML_FILE MODULE_FILE
"""
'''.lstrip()


def found_or_none(elem):
    return elem.text if elem is not None else None


# Take care of inconsistent quotes in standard name descriptions.
def replace_quote(txt):
    return txt.replace('"', "'") if txt is not None else None


def process_name_table(tree, element_name, *child_elements):
    """
    Yields a series of dictionaries with the key being the id of the entry element and the value containing
    another dictionary mapping other attributes of the standard name to their values, e.g. units, description, grib value etc.
    """
    for elem in tree.iterfind(element_name):
        sub_section = {}
        for child_elem in child_elements:
            sub_section[child_elem] = found_or_none(elem.find(child_elem))
        yield {elem.get("id") : sub_section}


def prettydict(outfile, varname, data):
    """Pretty formatted output of the data (dict) assigned to the variable 'varname'."""
    outfile.write(f'{varname} = {{\n')
    for k, v in dict(sorted(data.items())).items():
        outfile.write(f'    "{k}": "{v}",\n')
    outfile.write("}\n\n")


def decode_version(outfile, tree):
    """Decode the version information in the xml header information."""
    version = {}
    for elem in ["table_name", "version_number", "last_modified", "institution", "contact"]:
        version[elem] = found_or_none(tree.find(elem))
    if version["table_name"] is None:
        if (version["institution"] == "Centre for Environmental Data Analysis"
                and version["contact"] == "support@ceda.ac.uk"):
            version["table_name"] = "CF-StdNameTable"
        else:
            version["table_name"] = "USER-StdNameTable"
    prettydict(outfile, "VERSION", version)
    version_string = "-".join(version[k] for k in ["table_name", "version_number"])
    outfile.write(f'CONVENTIONS_STRING = "{version_string}"\n\n')


def write_useful_variables(outfile):
    outfile.write(
        '\n# The following variables are used for processing the standard names information below\n'
        '_ACCEPT = "accept"\n'
        '_WARN = "warn"\n'
        '_REPLACE ="replace"\n'
        '_ALTERNATIVE_MODES = [_ACCEPT, _WARN, _REPLACE]\n'
        '_DEFAULT = "warn"\n'
        '_MODE = _DEFAULT\n\n'
    )


def decode_standard_name_table(infile, outfile, description=False):
    """Process the different parts of the xml file."""
    tree = ET.parse(infile)

    outfile.write(STD_NAME_TABLE_FILE_TEMPLATE)
    write_useful_variables(outfile)
    decode_version(outfile, tree)

    data = {}
    for section in process_name_table(tree, 'entry', 'canonical_units'):
        data.update(section)
    prettydict(outfile, "STD_NAMES", data)

    data = {}
    for section in process_name_table(tree, 'alias', 'entry_id'):
        for k, v in section.items():
            data.update({k: v["entry_id"]})
    prettydict(outfile, "ALIASES", data)

    if description:
        data = {}
        for section in process_name_table(tree, 'entry', 'description'):
            for k, v in section.items():
                data.update({k: replace_quote(v["description"])})
        prettydict(outfile, "DESCRIPTIONS", data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Create Python code from CF standard name XML.')
    parser.add_argument('input', metavar='INPUT',
                        help='Path to CF standard name XML')
    parser.add_argument('output', metavar='OUTPUT',
                        help='Path to resulting Python code')
    parser.add_argument('-d', '--descr', action="store_true",
                        help="Include standard name descriptions")
    args = parser.parse_args()

    encoding = {'encoding': 'utf-8'}

    with open(args.input, 'r', **encoding) as in_fh:
        with open(args.output, 'w', **encoding) as out_fh:
            decode_standard_name_table(in_fh, out_fh, args.descr)
            pass
