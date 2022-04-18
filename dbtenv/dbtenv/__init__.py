# Standard library
from abc import ABC as AbstractBaseClass, abstractmethod
import argparse
import distutils.version
from enum import Enum
import logging
import os
import os.path
import platform
import re
import subprocess
import sys
from typing import Any, List, Optional


DEFAULT_VENVS_DIRECTORY = os.path.normpath('~/.dbt/versions')

GLOBAL_VERSION_FILE = os.path.normpath('~/.dbt/version')
LOCAL_VERSION_FILE  = '.dbt_version'
DBT_VERSION_VAR     = 'DBT_VERSION'

AUTO_INSTALL_VAR          = 'DBTENV_AUTO_INSTALL'
DEBUG_VAR                 = 'DBTENV_DEBUG'
DEFAULT_INSTALLER_VAR     = 'DBTENV_DEFAULT_INSTALLER'
PYTHON_VAR                = 'DBTENV_PYTHON'
QUIET_VAR                 = 'DBTENV_QUIET'
SIMULATE_RELEASE_DATE_VAR = 'DBTENV_SIMULATE_RELEASE_DATE'
VENVS_DIRECTORY_VAR       = 'DBTENV_VENVS_DIRECTORY'


def string_is_true(value: str) -> bool:
    return value.strip().lower() in ('1', 'active', 'enable', 'enabled', 'on', 't', 'true', 'y', 'yes')


LOGGER = logging.getLogger('dbtenv')
output_handler = logging.StreamHandler()
output_handler.setFormatter(logging.Formatter('{name} {levelname}:  {message}', style='{'))
output_handler.setLevel(logging.DEBUG)
LOGGER.addHandler(output_handler)
LOGGER.propagate = False
LOGGER.setLevel(logging.DEBUG if string_is_true(os.environ.get(DEBUG_VAR, '')) else logging.INFO)
logger = LOGGER

# Lowercase the less critical levels so they don't attract as much attention.
logging.addLevelName(logging.DEBUG, 'debug')
logging.addLevelName(logging.INFO, 'info')


class DbtenvError(RuntimeError):
    pass


class DbtError(RuntimeError):
    def __init__(self, exit_code: int) -> None:
        super().__init__(f"dbt execution failed with exit code {exit_code}.")
        self.exit_code = exit_code


class Args(argparse.Namespace):
    def get(self, name: str, default: Optional[Any] = None) -> Optional[Any]:
        return getattr(self, name, default)


class Installer(Enum):
    PIP      = 'pip'

    def __str__(self) -> str:
        return self.value


class Version(distutils.version.LooseVersion):
    def __init__(self, pip_specifier: str = None, adapter_type: str = None, version: str = None, source: Optional[str] = None, source_description: Optional[str] = None) -> None:
        if pip_specifier:
            self.pip_specifier = pip_specifier
            self.name, self.version = re.match(r"^(dbt-.+)==(.+)$", pip_specifier).groups()
            self.adapter_type = self.name.replace("dbt-", "")
            self.pypi_version = self.version
        else:
            self.adapter_type = adapter_type
            self.name = f"dbt-{adapter_type}"
            self.pypi_version = version
            self.pip_specifier = f"{self.name}=={self.pypi_version}"
        if not self.name.startswith('dbt'):
            raise(Exception)
        self.source_description = source_description
        self.source = source

        version_match = re.match(r'(?P<version>\d+\.\d+\.\d+)(-?(?P<prerelease>[a-z].*))?', self.pypi_version)
        self.is_semantic = version_match is not None
        self.is_stable = version_match is not None and not version_match['prerelease']
        self.major_minor_patch = version_match['version'] if version_match is not None else None
        self.prerelease = version_match['prerelease'] if version_match is not None else None

        # dbt pre-release versions are formatted slightly differently.
        if version_match and version_match['prerelease']:
            self.pypi_version     = f"{version_match['version']}{version_match['prerelease']}"

        super().__init__(self.pypi_version)

    def __hash__(self) -> int:
        return self.pypi_version.__hash__()

    def __str__(self) -> str:
        return self.pip_specifier

    def __repr__(self) -> str:
        return f"Version('{self.pip_specifier}')"

    def _cmp(self, other: 'Position') -> int:
        if self.name < other.name:
            return -1
        if self.name > other.name:
            return 1
        if self.pypi_version == other.pypi_version:
            return 0
        if self.pypi_version < other.pypi_version:
            return -1
        if self.pypi_version > other.pypi_version:
            return 1

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, source):
        if source and not self.source_description:
            self.source_description = f"set by {source}"
        self._source = source

    def get_installer_version(self, installer: Installer) -> str:
        return self.pypi_version


class Environment:
    def __init__(self) -> None:
        self.os = platform.system()
        if self.os == 'Darwin':
            self.os = 'Mac'

        self.env_vars = os.environ

        self.working_directory = os.getcwd()

        self.project_file = self.find_file_along_working_path('dbt_project.yml')
        self.project_directory = os.path.dirname(self.project_file) if self.project_file else None

        self.venvs_directory = os.path.expanduser(self.env_vars.get(VENVS_DIRECTORY_VAR) or DEFAULT_VENVS_DIRECTORY)

        self.global_version_file = os.path.expanduser(GLOBAL_VERSION_FILE)

    _debug: Optional[bool] = None

    @property
    def debug(self) -> bool:
        if self._debug is None:
            if DEBUG_VAR in self.env_vars:
                self._debug = string_is_true(self.env_vars[DEBUG_VAR])
            else:
                self._debug = False

        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self._debug = value
        self.update_logging_level()

    _quiet: Optional[bool] = None

    @property
    def quiet(self) -> bool:
        if self._quiet is None:
            if QUIET_VAR in self.env_vars:
                self._quiet = string_is_true(self.env_vars[QUIET_VAR])
            else:
                self._quiet = False

        return self._quiet

    @quiet.setter
    def quiet(self, value: bool) -> None:
        self._quiet = value
        self.update_logging_level()

    def update_logging_level(self) -> None:
        if self.debug:
            LOGGER.setLevel(logging.DEBUG)
        elif self.quiet:
            LOGGER.setLevel(logging.ERROR)
        else:
            LOGGER.setLevel(logging.INFO)

    _default_installer: Optional[Installer] = None

    @property
    def default_installer(self) -> Installer:
        self._default_installer = Installer.PIP

        return self._default_installer

    _installer: Optional[Installer] = None

    @property
    def installer(self) -> Optional[Installer]:
        return self._installer

    @installer.setter
    def installer(self, value: Installer) -> None:
        self._installer = value

    @property
    def primary_installer(self) -> Installer:
        return self.installer or self.default_installer

    @property
    def use_pip(self) -> bool:
        return not self.installer or self.installer == Installer.PIP

    _python: Optional[str] = None

    @property
    def python(self) -> str:
        if self._python is None:
            if PYTHON_VAR in self.env_vars:
                self._python = self.env_vars[PYTHON_VAR]
            else:
                # If dbtenv is installed in a virtual environment use the base Python installation's executable.
                base_exec_path = sys.base_exec_prefix
                possible_python_subpaths = ['python.exe'] if self.os == 'Windows' else ['bin/python3', 'bin/python']
                for possible_python_subpath in possible_python_subpaths:
                    python_path = os.path.join(base_exec_path, possible_python_subpath)
                    if os.path.isfile(python_path):
                        logger.debug(f"Found Python executable `{python_path}`.")
                        self._python = python_path
                        break
                else:
                    raise DbtenvError(f"No Python executable found in `{base_exec_path}`.")

        return self._python

    @python.setter
    def python(self, value: str) -> None:
        self._python = value

    _auto_install: Optional[bool] = None

    @property
    def auto_install(self) -> bool:
        if self._auto_install is None:
            if AUTO_INSTALL_VAR in self.env_vars:
                self._auto_install = string_is_true(self.env_vars[AUTO_INSTALL_VAR])
            else:
                self._auto_install = True

        return self._auto_install

    _simulate_release_date: Optional[bool] = None

    @property
    def simulate_release_date(self) -> bool:
        if self._simulate_release_date is None:
            if SIMULATE_RELEASE_DATE_VAR in self.env_vars:
                self._simulate_release_date = string_is_true(self.env_vars[SIMULATE_RELEASE_DATE_VAR])
            else:
                self._simulate_release_date = False

        return self._simulate_release_date

    @simulate_release_date.setter
    def simulate_release_date(self, value: bool) -> None:
        self._simulate_release_date = value

    def find_file_along_working_path(self, file_name: str) -> Optional[str]:
        search_dir = self.working_directory
        while True:
            file_path = os.path.join(search_dir, file_name)
            if os.path.isfile(file_path):
                return file_path

            parent_dir = os.path.dirname(search_dir)
            if parent_dir == search_dir:
                break

            search_dir = parent_dir

        return None


class Subcommand(AbstractBaseClass):
    """A dbtenv sub-command, which can be executed."""

    def __init__(self, env: Environment) -> None:
        self.env = env

    @abstractmethod
    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        pass

    @abstractmethod
    def execute(self, args: Args) -> None:
        pass


class Dbt(AbstractBaseClass):
    """A specific version of dbt, which can be installed, executed, and uninstalled."""

    def __init__(self, env: Environment, version: Version) -> None:
        self.env = env
        self.version = version

    @abstractmethod
    def install(self, force: bool = False) -> None:
        pass

    def is_installed(self) -> bool:
        return self.try_get_executable() is not None

    @abstractmethod
    def get_executable(self) -> str:
        pass

    def try_get_executable(self) -> Optional[str]:
        try:
            return self.get_executable()
        except Exception as error:
            logger.debug(f"Error getting executable:  {error}")
            return None

    def execute(self, args: List[str]) -> None:
        executable = self.get_executable()
        logger.debug(f"Running `{executable}` with arguments {args}.")
        # We don't use subprocess.run() here because if a KeyboardInterrupt happens it would only wait 0.25 seconds
        # before killing the dbt process.
        with subprocess.Popen([executable, *args]) as process:
            try:
                process.communicate()
                return_code = process.poll()
            except KeyboardInterrupt:
                try:
                    # Give dbt time to wrap things up (e.g. cancelling any running queries).
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise
            except:
                process.kill()
                raise

        if return_code is not None and return_code != 0:
            raise DbtError(return_code)

    @abstractmethod
    def uninstall(self, force: bool = False) -> None:
        pass
