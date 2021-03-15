import logging
import os
import os.path
import sys
from typing import Optional


VERSIONS_DIRECTORY      = os.path.normpath('~/.dbt/versions')
VERSIONS_DIRECTORY_PATH = os.path.expanduser(VERSIONS_DIRECTORY)

GLOBAL_VERSION_FILE      = os.path.normpath('~/.dbt/version')
GLOBAL_VERSION_FILE_PATH = os.path.expanduser(GLOBAL_VERSION_FILE)

LOCAL_VERSION_FILE = '.dbt_version'

DBT_VERSION_VAR           = 'DBT_VERSION'
PYTHON_VAR                = 'DBTENV_PYTHON'
AUTO_INSTALL_VAR          = 'DBTENV_AUTO_INSTALL'
SIMULATE_RELEASE_DATE_VAR = 'DBTENV_SIMULATE_RELEASE_DATE'
DEBUG_VAR                 = 'DBTENV_DEBUG'

DBT_PACKAGE_JSON_URL = 'https://pypi.org/pypi/dbt/json'

LOGGER = logging.getLogger('dbtenv')
output_handler = logging.StreamHandler()
output_handler.setFormatter(logging.Formatter('{name} {levelname}:  {message}', style='{'))
output_handler.setLevel(logging.DEBUG)
LOGGER.addHandler(output_handler)
LOGGER.propagate = False
LOGGER.setLevel(logging.INFO)
logger = LOGGER


class DbtenvError(RuntimeError):
    pass


class DbtError(RuntimeError):
    def __init__(self, exit_code):
        super().__init__(f"dbt execution failed with exit code {exit_code}.")
        self.exit_code = exit_code


def get_version_directory(dbt_version: str) -> str:
    return os.path.join(VERSIONS_DIRECTORY_PATH, dbt_version)


class Config:
    def __init__(self):
        # Enable debug logging during initialization if it's configured.
        self.debug = self.debug

    _debug: Optional[bool] = None

    @property
    def debug(self) -> bool:
        if self._debug is not None:
            return self._debug

        if DEBUG_VAR in os.environ:
            self._debug = self._string_is_true(os.environ[DEBUG_VAR])
            return self._debug

        self._debug = False
        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self._debug = value
        LOGGER.setLevel(logging.DEBUG if self._debug else logging.INFO)

    _python: Optional[str] = None

    @property
    def python(self) -> str:
        if self._python:
            return self._python

        if PYTHON_VAR in os.environ:
            self._python = os.environ[PYTHON_VAR]
            return self._python

        # If dbtenv is installed in a virtual environment use the base Python installation's executable.
        base_exec_path = sys.base_exec_prefix
        for possible_python_subpath_parts in [['bin', 'python3'], ['bin', 'python'], ['python.exe']]:
            python_path = os.path.join(base_exec_path, *possible_python_subpath_parts)
            if os.path.isfile(python_path):
                logger.debug(f"Found Python executable `{python_path}`.")
                self._python = python_path
                return self._python

        raise DbtenvError(f"No Python executable found in `{base_exec_path}`.")

    @python.setter
    def python(self, value: str) -> None:
        self._python = value

    _auto_install: Optional[bool] = None

    @property
    def auto_install(self) -> bool:
        if self._auto_install is not None:
            return self._auto_install

        if AUTO_INSTALL_VAR in os.environ:
            self._auto_install = self._string_is_true(os.environ[AUTO_INSTALL_VAR])
            return self._auto_install

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
            self._simulate_release_date = self._string_is_true(os.environ[SIMULATE_RELEASE_DATE_VAR])
            return self._simulate_release_date

        self._simulate_release_date = False
        return self._simulate_release_date

    @simulate_release_date.setter
    def simulate_release_date(self, value: bool) -> None:
        self._simulate_release_date = value

    def _string_is_true(self, value: str) -> bool:
        return value.strip().lower() in ('1', 'active', 'enable', 'enabled', 'on', 't', 'true', 'y', 'yes')

CONFIG = Config()
