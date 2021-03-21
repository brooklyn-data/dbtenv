from abc import ABC as AbstractBaseClass, abstractmethod
import argparse
import distutils.version
from enum import Enum
import logging
import os
import os.path
import platform
import re
import shutil
import subprocess
import sys
from typing import Any, List, Optional, Tuple


VENVS_DIRECTORY = os.path.normpath('~/.dbt/versions')

GLOBAL_VERSION_FILE = os.path.normpath('~/.dbt/version')
LOCAL_VERSION_FILE  = '.dbt_version'
DBT_VERSION_VAR     = 'DBT_VERSION'

AUTO_INSTALL_VAR          = 'DBTENV_AUTO_INSTALL'
DEBUG_VAR                 = 'DBTENV_DEBUG'
DEFAULT_INSTALLER_VAR     = 'DBTENV_DEFAULT_INSTALLER'
PYTHON_VAR                = 'DBTENV_PYTHON'
SIMULATE_RELEASE_DATE_VAR = 'DBTENV_SIMULATE_RELEASE_DATE'


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
    HOMEBREW = 'homebrew'

    def __str__(self) -> str:
        return self.value


class Version(distutils.version.LooseVersion):
    def __init__(self, version: str) -> None:
        self.pypi_version = self.homebrew_version = self.raw_version = version

        # dbt pre-release versions are formatted slightly differently in PyPI and Homebrew.
        prerelease_match = re.match(r'(?P<version>\d+(\.\d+)+)-?(?P<prerelease>[a-z].*)', version)
        if prerelease_match:
            self.pypi_version     = f"{prerelease_match['version']}{prerelease_match['prerelease']}"
            self.homebrew_version = f"{prerelease_match['version']}-{prerelease_match['prerelease']}"

        # Standardize on the PyPI version for comparison and hashing.
        super().__init__(self.pypi_version)

    def __hash__(self) -> int:
        return self.pypi_version.__hash__()

    def __str__(self) -> str:
        return self.raw_version

    def __repr__(self) -> str:
        return f"Version('{self.raw_version}')"

    def _cmp(self, other: Any) -> int:
        # Comparing standard integer-based versions to non-standard text versions will raise a TypeError.
        # In such cases we'll fall back to comparing the entire version strings rather than the individual parts.
        try:
            return super()._cmp(other)
        except:
            if isinstance(other, str):
                return self._str_cmp(other)
            if isinstance(other, Version):
                return self._str_cmp(other.pypi_version)
            raise

    def _str_cmp(self, other: str) -> int:
        if self.pypi_version == other:
            return 0
        if self.pypi_version < other:
            return -1
        if self.pypi_version > other:
            return 1

    def get_installer_version(self, installer: Installer) -> str:
        if installer == Installer.PIP:
            return self.pypi_version
        elif installer == Installer.HOMEBREW:
            return self.homebrew_version
        else:
            return self.raw_version


class Environment:
    def __init__(self) -> None:
        self.os = platform.system()
        if self.os == 'Darwin':
            self.os = 'Mac'

        self.env_vars = os.environ

        self.working_directory = os.getcwd()

        self.venvs_directory     = os.path.expanduser(VENVS_DIRECTORY)
        self.global_version_file = os.path.expanduser(GLOBAL_VERSION_FILE)

        self.homebrew_installed = False
        self.homebrew_prefix_directory = self.env_vars.get('HOMEBREW_PREFIX')
        if not self.homebrew_prefix_directory and self.os != 'Windows':
            brew_executable = shutil.which('brew')
            if brew_executable:
                self.homebrew_prefix_directory = os.path.dirname(os.path.dirname(brew_executable))
        if self.homebrew_prefix_directory and os.path.isdir(self.homebrew_prefix_directory):
            self.homebrew_installed = True
            logger.debug(f"Homebrew is installed with prefix `{self.homebrew_prefix_directory}`.")

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
        LOGGER.setLevel(logging.DEBUG if self._debug else logging.INFO)

    _default_installer: Optional[Installer] = None

    @property
    def default_installer(self) -> Installer:
        if self._default_installer is None:
            if DEFAULT_INSTALLER_VAR in self.env_vars:
                self._default_installer = Installer(self.env_vars[DEFAULT_INSTALLER_VAR].lower())
            else:
                self._default_installer = Installer.PIP

        return self._default_installer

    _installer: Optional[Installer] = None

    @property
    def installer(self) -> Optional[Installer]:
        return self._installer

    @installer.setter
    def installer(self, value: Installer) -> None:
        self._installer = value

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
                self._auto_install = False

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

    def try_get_version_and_source(self) -> Tuple[Optional[Version], Optional[str]]:
        shell_version = self.try_get_shell_version()
        if shell_version:
            return shell_version, f"{DBT_VERSION_VAR} environment variable"

        local_version, version_file = self.try_get_local_version_and_source()
        if local_version:
            return local_version, f"`{version_file}`"

        global_version = self.try_get_global_version()
        if global_version:
            return global_version, f"`{self.global_version_file}`"

        return None, None

    def try_get_global_version(self) -> Optional[Version]:
        if os.path.isfile(self.global_version_file):
            return self._read_version_file(self.global_version_file)

        return None

    def set_global_version(self, version: Version) -> None:
        self._write_version_file(self.global_version_file, version)
        logger.info(f"{version} is now set as the global dbt version in `{self.global_version_file}`.")

    def try_get_local_version_and_source(self) -> Tuple[Optional[Version], Optional[str]]:
        search_dir = self.working_directory
        while True:
            version_file = os.path.join(search_dir, LOCAL_VERSION_FILE)
            if os.path.isfile(version_file):
                version = self._read_version_file(version_file)
                return version, version_file

            parent_dir = os.path.dirname(search_dir)
            if parent_dir == search_dir:
                break

            search_dir = parent_dir

        return None, None

    def set_local_version(self, version: Version) -> None:
        version_file = os.path.join(self.working_directory, LOCAL_VERSION_FILE)
        self._write_version_file(version_file, version)
        logger.info(f"{version} is now set as the local dbt version in `{version_file}`.")


    def try_get_shell_version(self) -> Optional[Version]:
        if DBT_VERSION_VAR in self.env_vars:
            return Version(self.env_vars[DBT_VERSION_VAR])

        return None

    def _read_version_file(self, file_path: str) -> Version:
        with open(file_path, 'r') as file:
            return Version(file.readline().strip())

    def _write_version_file(self, file_path: str, version: Version) -> None:
        with open(file_path, 'w') as file:
            file.write(str(version))


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
        except:
            return None

    def execute(self, args: List[str]) -> None:
        executable = self.get_executable()
        logger.debug(f"Running `{executable}` with arguments {args}.")
        dbt_result = subprocess.run([executable, *args])
        if dbt_result.returncode != 0:
            raise DbtError(dbt_result.returncode)

    @abstractmethod
    def uninstall(self, force: bool = False) -> None:
        pass
