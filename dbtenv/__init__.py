import argparse
import distutils.version
from enum import Enum
import logging
import os
import os.path
import platform
import re
import shutil
import sys
from typing import Any, Optional


VENVS_DIRECTORY = os.path.normpath('~/.dbt/versions')

GLOBAL_VERSION_FILE = os.path.normpath('~/.dbt/version')
LOCAL_VERSION_FILE  = '.dbt_version'
DBT_VERSION_VAR     = 'DBT_VERSION'

AUTO_INSTALL_VAR          = 'DBTENV_AUTO_INSTALL'
DEBUG_VAR                 = 'DBTENV_DEBUG'
DEFAULT_INSTALLER_VAR     = 'DBTENV_DEFAULT_INSTALLER'
PYTHON_VAR                = 'DBTENV_PYTHON'
SIMULATE_RELEASE_DATE_VAR = 'DBTENV_SIMULATE_RELEASE_DATE'

LOGGER = logging.getLogger('dbtenv')
output_handler = logging.StreamHandler()
output_handler.setFormatter(logging.Formatter('{name} {levelname}:  {message}', style='{'))
output_handler.setLevel(logging.DEBUG)
LOGGER.addHandler(output_handler)
LOGGER.propagate = False
LOGGER.setLevel(logging.INFO)
logger = LOGGER


def string_is_true(value: str) -> bool:
    return value.strip().lower() in ('1', 'active', 'enable', 'enabled', 'on', 't', 'true', 'y', 'yes')


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

    def get_installer_version(self, installer: Installer) -> str:
        if installer == Installer.PIP:
            return self.pypi_version
        elif installer == Installer.HOMEBREW:
            return self.homebrew_version
        else:
            return self.raw_version


class Environment:
    def __init__(self) -> None:
        # Enable debug logging during initialization if it's configured.
        self.debug = self.debug

        self.os = platform.system()
        if self.os == 'Darwin':
            self.os = 'Mac'

        self.venvs_directory     = os.path.expanduser(VENVS_DIRECTORY)
        self.global_version_file = os.path.expanduser(GLOBAL_VERSION_FILE)

        self.homebrew_installed = False
        self.homebrew_cellar_directory = os.environ.get('HOMEBREW_CELLAR')
        if not self.homebrew_cellar_directory and self.os != 'Windows':
            brew_executable = shutil.which('brew')
            if brew_executable:
                self.homebrew_cellar_directory = os.path.join(os.path.dirname(os.path.dirname(brew_executable)), 'Cellar')
        if self.homebrew_cellar_directory and os.path.isdir(self.homebrew_cellar_directory):
            self.homebrew_installed = True
            logger.debug(f"Homebrew is installed with cellar at `{self.homebrew_cellar_directory}`.")

    _debug: Optional[bool] = None

    @property
    def debug(self) -> bool:
        if self._debug is not None:
            return self._debug

        if DEBUG_VAR in os.environ:
            self._debug = string_is_true(os.environ[DEBUG_VAR])
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
        if self._default_installer:
            return self._default_installer

        if DEFAULT_INSTALLER_VAR in os.environ:
            self._default_installer = Installer(os.environ[DEFAULT_INSTALLER_VAR].lower())
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
        if self._python:
            return self._python

        if PYTHON_VAR in os.environ:
            self._python = os.environ[PYTHON_VAR]
        else:
            # If dbtenv is installed in a virtual environment use the base Python installation's executable.
            base_exec_path = sys.base_exec_prefix
            for possible_python_subpath_parts in [['bin', 'python3'], ['bin', 'python'], ['python.exe']]:
                python_path = os.path.join(base_exec_path, *possible_python_subpath_parts)
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
        if self._auto_install is not None:
            return self._auto_install

        if AUTO_INSTALL_VAR in os.environ:
            self._auto_install = string_is_true(os.environ[AUTO_INSTALL_VAR])
        else:
            self._auto_install = False

        return self._auto_install

    @auto_install.setter
    def auto_install(self, value: bool) -> None:
        self._auto_install = value

    _simulate_release_date: Optional[bool] = None

    @property
    def simulate_release_date(self) -> bool:
        if self._simulate_release_date is not None:
            return self._simulate_release_date

        if SIMULATE_RELEASE_DATE_VAR in os.environ:
            self._simulate_release_date = string_is_true(os.environ[SIMULATE_RELEASE_DATE_VAR])
        else:
            self._simulate_release_date = False

        return self._simulate_release_date

    @simulate_release_date.setter
    def simulate_release_date(self, value: bool) -> None:
        self._simulate_release_date = value

ENV = Environment()
