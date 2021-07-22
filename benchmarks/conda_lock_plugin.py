"""
ASV plug-in providing an alternative ``Environment`` subclass, which uses Nox
for environment management.

"""
from asv.console import log
from asv.plugins.conda import Conda, _find_conda

class CondaLock(Conda):
    """
    Create the environment based on a **version-controlled** lockfile.

    Creating the environment instance is deferred until ``install_project`` time,
    when the commit hash etc is known and we can access the lock file.
    The environment is then overwritten by the specification provided at the
    ``config.conda_lockfile`` path.  ``conda.conda_lockfile`` must point to
    an @EXPLICIT conda manifest, e.g. the output of either the ``conda-lock`` tool,
    or ``conda list --explicit``.
    """
    tool_name = "conda-lock"

    def _uninstall_project(self):
        if self._get_installed_commit_hash():
            # we can only run the uninstall command if an environment has already
            # been made before, otherwise there is no python to use to uninstall
            return super()._uninstall_project()

    def _setup(self):
        # create the shell of a conda environment, that includes no packages
        log.info("Creating conda environment for {0}".format(self.name))
        self.run_executable(_find_conda(), ['create', "-y", '-p', self._path, '--force'])

    def _build_project(self, repo, commit_hash, build_dir):
        # at "build" time, we build the environment from the provided lockfile
        self.run_executable(_find_conda(), ["install", "-y", "-p", self._path, "--file", f"{build_dir}/requirements/ci/nox.lock/py38-linux-64.lock"])
        # this is set to warning as the asv.commands.run._do_build function
        # explicitly raises the log level to WARN, and I want to see the environment being updated
        # in the stdout log.
        log.warning(f"Environment {self.name} updated to spec at {commit_hash[:8]}")
        log.debug(self.run_executable(_find_conda(), ["list", "-p", self._path]))
        # self._build_command = ""
        # return super()._build_project(repo, commit_hash, build_dir)

    def _install_project(self, repo, commit_hash, build_dir):
        self._install_command = "pip install --no-deps --editable {build_dir}"
        return super()._install_project(repo, commit_hash, build_dir)