import os
import sys

from setuptools import Command, setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop as develop_cmd


class BaseCommand(Command):
    """A valid no-op command for setuptools & distutils."""

    description = "A no-op command."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        pass


def build_std_names(cmd, directory):
    # Call out to tools/generate_std_names.py to build std_names module.

    script_path = os.path.join("tools", "generate_std_names.py")
    xml_path = os.path.join("etc", "cf-standard-name-table.xml")
    module_path = os.path.join(directory, "iris", "std_names.py")
    args = (sys.executable, script_path, xml_path, module_path)
    cmd.spawn(args)


def custom_cmd(command_to_override, functions, help_doc=""):
    """
    Allows command specialisation to include calls to the given functions.

    """

    class ExtendedCommand(command_to_override):
        description = help_doc or command_to_override.description

        def run(self):
            # Run the original command first to make sure all the target
            # directories are in place.
            command_to_override.run(self)

            if self.editable_mode:
                print(" [Running in-place]")
                # Pick the source dir instead (currently in the sub-dir "lib").
                dest = "lib"
            else:
                # Not editable - must be building.
                dest = self.build_lib

            for func in functions:
                func(self, dest)

    return ExtendedCommand


custom_commands = {
    "develop": custom_cmd(develop_cmd, [build_std_names]),
    "build_py": custom_cmd(build_py, [build_std_names]),
    "std_names": custom_cmd(
        BaseCommand,
        [build_std_names],
        help_doc="generate CF standard name module",
    ),
}


setup(
    cmdclass=custom_commands,
)
