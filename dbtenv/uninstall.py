import argparse
import os
import os.path
import re
import shutil
import subprocess

import dbtenv


logger = dbtenv.LOGGER


def build_uninstall_args_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        'uninstall',
        help="Uninstall the specified dbt version."
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help="Uninstall without prompting for confirmation."
    )
    parser.add_argument('dbt_version', metavar='<dbt_version>', help="Exact version of dbt to uninstall.")


def uninstall(parsed_args: argparse.Namespace) -> None:
    dbt_version = parsed_args.dbt_version
    dbt_version_dir = dbtenv.get_version_directory(dbt_version)
    if not os.path.isdir(dbt_version_dir):
        raise dbtenv.DbtenvRuntimeError(f"No dbt {dbt_version} installation found in `{dbt_version_dir}`.")

    if parsed_args.force or dbtenv.string_is_true(input(f"Uninstall dbt {dbt_version} from `{dbt_version_dir}`? ")):
        shutil.rmtree(dbt_version_dir)
        logger.info(f"Successfully uninstalled dbt {dbt_version} from `{dbt_version_dir}`.")
