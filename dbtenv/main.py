#!/usr/bin/env python3

import argparse
from collections import namedtuple
import logging
import sys
from typing import List

import dbtenv
import dbtenv.install
import dbtenv.uninstall


EXIT_CODES = namedtuple('ExitCodes', 'success failure')(success=0, failure=1)

logger = dbtenv.LOGGER


def build_args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="""
            Lets you easily install and switch between multiple versions of dbt in dedicated Python virtual environments.
        """,
        epilog="Run a sub-command with the `--help` option to see help for that sub-command."
    )
    parser.add_argument(
        '--python',
        metavar='PATH',
        help=f"""
            Path to the Python executable to use when installing dbt.
            The default is the Python executable used to install dbtenv, but that can be overridden by setting a
            {dbtenv.PYTHON_VAR} environment variable.
        """
    )
    parser.add_argument(
        '--auto-install',
        action='store_const',
        const=True,
        help=f"""
            Automatically install a specified dbt version if it isn't already installed.
            The default is to not auto-install, but that can be overridden by setting a {dbtenv.AUTO_INSTALL_VAR}
            environment variable.
        """
    )
    parser.add_argument(
        '--debug',
        action='store_const',
        const=True,
        help=f"""
            Output debug information as dbtenv runs.
            The default is to not output debug information, but that can be overridden by setting a {dbtenv.DEBUG_VAR}
            environment variable.
        """
    )

    subparsers = parser.add_subparsers(dest='subcommand', title="Sub-commands")
    dbtenv.install.build_install_args_parser(subparsers)
    dbtenv.uninstall.build_uninstall_args_parser(subparsers)

    return parser


def main(args: List[str] = None) -> None:
    try:
        if args is None:
            args = sys.argv[1:]

        args_parser = build_args_parser()
        parsed_args = args_parser.parse_args(args)
        if parsed_args.debug or dbtenv.get_debug_default():
            logger.setLevel(logging.DEBUG)
        logger.debug(f"Parsed arguments = {parsed_args}")

        subcommand = parsed_args.subcommand
        if not subcommand:
            args_parser.print_help()
            sys.exit(EXIT_CODES.failure)

        if subcommand == 'install':
            dbtenv.install.install(parsed_args)
        elif subcommand == 'uninstall':
            dbtenv.uninstall.uninstall(parsed_args)
        else:
            raise dbtenv.DbtenvRuntimeError(f"Unknown sub-command `{subcommand}`.")
    except dbtenv.DbtenvRuntimeError as error:
        logger.error(error)
        sys.exit(EXIT_CODES.failure)

    sys.exit(EXIT_CODES.success)
