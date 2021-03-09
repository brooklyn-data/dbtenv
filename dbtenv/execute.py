import argparse
import os
from typing import List

import dbtenv
import dbtenv.install
import dbtenv.version
import dbtenv.which


logger = dbtenv.LOGGER


def build_execute_args_parser(subparsers: argparse._SubParsersAction, parent_parser: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser(
        'execute',
        aliases=['exec'],
        parents=[parent_parser],
        description=f"""
            Execute a dbt command using the specified dbt version or the dbt version automatically detected from the
            environment based on the global `{dbtenv.GLOBAL_VERSION_FILE}` file, local `{dbtenv.LOCAL_VERSION_FILE}` files,
            or {dbtenv.DBT_VERSION_VAR} environment variable.
        """,
        help="Execute a dbt command using the specified dbt version or the dbt version automatically detected from the environment."
    )
    parser.add_argument(
        '--dbt',
        dest='dbt_version',
        metavar='<dbt_version>',
        help="""
            Exact version of dbt to execute.
            If not specified, the dbt version will be automatically detected from the environment.
        """
    )
    parser.add_argument(
        'dbt_args',
        nargs='*',
        metavar='<dbt_args>',
        help="""
            Arguments to pass to dbt.
            It's highly recommended to specify ` -- ` (two dashes with spaces on both sides) before this list of
            arguments so dbtenv doesn't try to interpret them.
        """
    )


def run_execute_command(parsed_args: argparse.Namespace) -> None:
    if parsed_args.dbt_version:
        dbt_version = parsed_args.dbt_version
    else:
        dbt_version, dbt_version_source = dbtenv.version.get_version(os.getcwd())
        logger.info(f"Using dbt {dbt_version} (set by {dbt_version_source}).")

    dbtenv.install.ensure_dbt_version_installed(dbt_version)

    execute_dbt(dbt_version, parsed_args.dbt_args)


def execute_dbt(dbt_version: str, args: List[str]) -> None:
    dbt = dbtenv.which.get_dbt(dbt_version)
    dbt_process_args = [dbt, *args]
    logger.debug(f"Running `{dbt}` with arguments {args}.")

    # Execute dbt, replacing the current process.
    os.execv(dbt, dbt_process_args)
