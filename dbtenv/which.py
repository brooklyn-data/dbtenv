import argparse
import os
from typing import Optional

import dbtenv
import dbtenv.version


logger = dbtenv.LOGGER


def build_which_args_parser(subparsers: argparse._SubParsersAction, parent_parser: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser(
        'which',
        parents=[parent_parser],
        description=f"""
            Show the full path to the executable of the specified dbt version or the dbt version automatically detected
            from the environment based on the global `{dbtenv.GLOBAL_VERSION_FILE}` file, local
            `{dbtenv.LOCAL_VERSION_FILE}` files, or {dbtenv.DBT_VERSION_VAR} environment variable.
        """,
        help="""
            Show the full path to the executable of the specified dbt version or the dbt version automatically detected
            from the environment.
        """
    )
    parser.add_argument(
        'dbt_version',
        nargs='?',
        metavar='<dbt_version>',
        help="""
            Exact version of dbt to show.
            If not specified, the dbt version will be automatically detected from the environment.
        """
    )


def run_which_command(parsed_args: argparse.Namespace) -> None:
    if parsed_args.dbt_version:
        dbt_version = parsed_args.dbt_version
    else:
        dbt_version, dbt_version_source = dbtenv.version.get_version(os.getcwd())
        logger.info(f"Using dbt {dbt_version} (set by {dbt_version_source}).")

    print(get_dbt(dbt_version))


def get_dbt(dbt_version: str) -> str:
    dbt_version_dir = dbtenv.get_version_directory(dbt_version)
    if not os.path.isdir(dbt_version_dir):
        raise dbtenv.DbtenvRuntimeError(f"No dbt {dbt_version} installation found in `{dbtenv.get_versions_directory()}`.")

    for possible_dbt_subpath_parts in [['bin', 'dbt'], ['Scripts', 'dbt.exe']]:
        dbt_path = os.path.join(dbt_version_dir, *possible_dbt_subpath_parts)
        if os.path.isfile(dbt_path):
            logger.debug(f"Found dbt executable `{dbt_path}`.")
            return dbt_path

    raise dbtenv.DbtenvRuntimeError(f"No dbt executable found in `{dbt_version_dir}`.")


def try_get_dbt(dbt_version: str) -> Optional[str]:
    try:
        return get_dbt(dbt_version)
    except:
        return None
