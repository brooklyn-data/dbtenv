import argparse
import os
import os.path
from typing import Optional, Tuple

import dbtenv
import dbtenv.install


logger = dbtenv.LOGGER


def build_version_args_parser(subparsers: argparse._SubParsersAction) -> None:
    description = """
        Show the dbt version automatically detected from the environment, or show/set the dbt version globally, for the
        local directory, or for the current shell.
    """
    parser = subparsers.add_parser(
        'version',
        description=description,
        help=description
    )
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        '--global',
        dest='global_dbt_version',
        nargs='?',
        const='',
        metavar='<dbt_version>',
        help=f"Show/set the dbt version globally using the `{dbtenv.GLOBAL_VERSION_FILE}` file."
    )
    scope_group.add_argument(
        '--local',
        dest='local_dbt_version',
        nargs='?',
        const='',
        metavar='<dbt_version>',
        help=f"Show/set the dbt version for the local directory using `{dbtenv.LOCAL_VERSION_FILE}` files."
    )
    scope_group.add_argument(
        '--shell',
        dest='shell_dbt_version',
        action='store_const',
        const=True,
        help=f"Show the dbt version set for the current shell using a {dbtenv.DBT_VERSION_VAR} environment variable."
    )


def run_version_command(parsed_args: argparse.Namespace) -> None:
    if parsed_args.global_dbt_version is not None:
        if parsed_args.global_dbt_version:
            set_global_version(parsed_args.global_dbt_version)
        else:
            global_version = get_global_version()
            if global_version:
                print(global_version)
            else:
                logger.info("No global dbt version has been set.")
    elif parsed_args.local_dbt_version is not None:
        working_dir = os.getcwd()
        if parsed_args.local_dbt_version:
            set_local_version(working_dir, parsed_args.local_dbt_version)
        else:
            local_version, version_file = get_local_version(working_dir)
            if local_version:
                print(f"{local_version}  (set by `{version_file}`)")
            else:
                logger.info(f"No local dbt version has been set for `{working_dir}` using `{dbtenv.LOCAL_VERSION_FILE}` files.")
    elif parsed_args.shell_dbt_version is not None:
        shell_version = get_shell_version()
        if shell_version:
            print(shell_version)
        else:
            logger.info(f"No dbt version has been set for the current shell using a {dbtenv.DBT_VERSION_VAR} environment variable.")
    else:
        version, source = get_version(os.getcwd())
        if version:
            print(f"{version}  (set by {source})")
        else:
            logger.info("No dbt version has been set globally, for the local directory, or for the current shell.")


def get_version(working_directory: str) -> Tuple[Optional[str], Optional[str]]:
    shell_version = get_shell_version()
    if shell_version:
        return shell_version, f"{dbtenv.DBT_VERSION_VAR} environment variable"

    local_version, version_file = get_local_version(working_directory)
    if local_version:
        return local_version, f"`{version_file}`"

    global_version = get_global_version()
    if global_version:
        return global_version, f"`{dbtenv.get_global_version_file()}`"

    return None, None


def get_global_version() -> Optional[str]:
    global_version_file = dbtenv.get_global_version_file()
    if os.path.isfile(global_version_file):
        return _read_file_line(global_version_file)

    return None


def set_global_version(dbt_version: str) -> None:
    ensure_dbt_version_installed(dbt_version)
    version_file = dbtenv.get_global_version_file()
    _write_file_line(version_file, dbt_version)
    logger.info(f"{dbt_version} is now set as the global dbt version in `{version_file}`.")


def get_local_version(working_directory: str) -> Tuple[Optional[str], Optional[str]]:
    search_dir = working_directory
    while True:
        version_file = os.path.join(search_dir, dbtenv.LOCAL_VERSION_FILE)
        if os.path.isfile(version_file):
            version = _read_file_line(version_file)
            return version, version_file

        parent_dir = os.path.dirname(search_dir)
        if parent_dir == search_dir:
            break

        search_dir = parent_dir

    return None, None


def set_local_version(working_directory: str, dbt_version: str) -> None:
    ensure_dbt_version_installed(dbt_version)
    version_file = os.path.join(working_directory, dbtenv.LOCAL_VERSION_FILE)
    _write_file_line(version_file, dbt_version)
    logger.info(f"{dbt_version} is now set as the local dbt version in `{version_file}`.")


def get_shell_version() -> Optional[str]:
    if dbtenv.DBT_VERSION_VAR in os.environ:
        return os.environ[dbtenv.DBT_VERSION_VAR]

    return None


def ensure_dbt_version_installed(dbt_version: str) -> None:
    if not os.path.isdir(dbtenv.get_version_directory(dbt_version)):
        if dbtenv.get_auto_install():
            dbtenv.install.install(dbt_version)
        else:
            raise dbtenv.DbtenvRuntimeError(
                f"No dbt {dbt_version} installation found in `{dbtenv.get_versions_directory()}` and auto-install is not enabled."
            )


def _read_file_line(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.readline().strip()


def _write_file_line(file_path: str, line: str) -> None:
    with open(file_path, 'w') as file:
        file.write(line)
