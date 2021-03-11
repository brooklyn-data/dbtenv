import argparse
import os
import os.path
import shutil
from typing import List

import dbtenv


logger = dbtenv.LOGGER


def build_uninstall_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    description = "Uninstall the specified dbt version."
    parser = subparsers.add_parser(
        'uninstall',
        parents=parent_parsers,
        description=description,
        help=description
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help="Uninstall without prompting for confirmation."
    )
    parser.add_argument('dbt_version', metavar='<dbt_version>', help="Exact version of dbt to uninstall.")


def run_uninstall_command(parsed_args: argparse.Namespace) -> None:
    uninstall(
        parsed_args.dbt_version,
        force=parsed_args.force
    )


def uninstall(dbt_version: str, force: bool = False) -> None:
    dbt_version_dir = dbtenv.get_version_directory(dbt_version)
    if not os.path.isdir(dbt_version_dir):
        raise dbtenv.DbtenvError(f"No dbt {dbt_version} installation found in `{dbtenv.get_versions_directory()}`.")

    if force or dbtenv.string_is_true(input(f"Uninstall dbt {dbt_version} from `{dbt_version_dir}`? ")):
        shutil.rmtree(dbt_version_dir)
        logger.info(f"Successfully uninstalled dbt {dbt_version} from `{dbt_version_dir}`.")
