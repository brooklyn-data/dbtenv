import logging
import os
import os.path
import sys


VERSIONS_DIRECTORY  = '~/.dbt/versions'
GLOBAL_VERSION_FILE = '~/.dbt/version'

PYTHON_VAR       = 'DBTENV_PYTHON'
AUTO_INSTALL_VAR = 'DBTENV_AUTO_INSTALL'
DEBUG_VAR        = 'DBTENV_DEBUG'


output_handler = logging.StreamHandler()
output_handler.setFormatter(logging.Formatter('{name} {levelname}:  {message}', style='{'))
output_handler.setLevel(logging.DEBUG)

LOGGER = logging.getLogger('dbtenv')
LOGGER.addHandler(output_handler)
LOGGER.propagate = False
LOGGER.setLevel(logging.INFO)
logger = LOGGER


class DbtenvRuntimeError(RuntimeError):
    pass


def string_is_true(string: str) -> bool:
    return isinstance(string, str) and string.strip().lower() in ('1', 't', 'true', 'y', 'yes')


def get_versions_directory_default() -> str:
    return os.path.expanduser(VERSIONS_DIRECTORY)


def get_version_directory(dbt_version: str) -> str:
    return os.path.join(get_versions_directory_default(), dbt_version)


def get_global_version_file_default() -> str:
    return os.path.expanduser(GLOBAL_VERSION_FILE)


def get_python_default() -> str:
    if PYTHON_VAR in os.environ:
        return os.environ[PYTHON_VAR]

    # If dbtenv is installed in a virtual environment use the base Python installation's executable.
    base_exec_path = sys.base_exec_prefix
    for possible_python_subpath_parts in [['bin', 'python3'], ['bin', 'python'], ['python.exe']]:
        python_path = os.path.join(base_exec_path, *possible_python_subpath_parts)
        if os.path.isfile(python_path):
            logger.debug(f"Found Python executable `{python_path}`.")
            return python_path

    raise DbtenvRuntimeError(f"No Python executable found in `{base_exec_path}`.")


def get_auto_install_default() -> bool:
    return string_is_true(os.environ.get(AUTO_INSTALL_VAR))


def get_debug_default() -> bool:
    return string_is_true(os.environ.get(DEBUG_VAR))
