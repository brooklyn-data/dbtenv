import argparse
import os
import subprocess
from typing import List

import dbtenv
import dbtenv.install
import dbtenv.version
import dbtenv.which


logger = dbtenv.LOGGER


def build_execute_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        'execute',
        aliases=['exec'],
        parents=parent_parsers,
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
        type=dbtenv.Version,
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


def run_execute_command(args: dbtenv.Args) -> None:
    if args.dbt_version:
        dbt_version = args.dbt_version
    else:
        dbt_version, dbt_version_source = dbtenv.version.get_version(os.getcwd())
        if dbt_version:
            logger.info(f"Using dbt {dbt_version} (set by {dbt_version_source}).")
        else:
            raise dbtenv.DbtenvError("No dbt version has been set globally, for the local directory, or for the current shell.")

    execute_dbt(dbt_version, args.dbt_args)


def execute_dbt(dbt_version: dbtenv.Version, args: List[str]) -> None:
    dbt = dbtenv.which.try_get_dbt(dbt_version)
    if not dbt:
        if dbtenv.ENV.auto_install:
            dbtenv.install.install(dbt_version)
            dbt = dbtenv.which.get_dbt(dbt_version)
        else:
            raise dbtenv.DbtenvError(f"No dbt {dbt_version} installation found and auto-install is not enabled.")

    logger.debug(f"Running `{dbt}` with arguments {args}.")
    dbt_result = subprocess.run([dbt, *args])
    if dbt_result.returncode != 0:
        raise dbtenv.DbtError(dbt_result.returncode)
