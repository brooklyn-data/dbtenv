import argparse
from collections import namedtuple
import sys
from typing import List

import dbtenv
import dbtenv.execute
import dbtenv.install
import dbtenv.uninstall
import dbtenv.version
import dbtenv.versions
import dbtenv.which


EXIT_CODES = namedtuple('ExitCodes', 'success failure')(success=0, failure=1)

logger = dbtenv.LOGGER


def build_args_parser() -> argparse.ArgumentParser:
    command_common_args_parser    = _build_common_args_parser()
    subcommand_common_args_parser = _build_common_args_parser(dest_prefix='subcommand_')

    parser = argparse.ArgumentParser(
        description="""
            Lets you easily install and switch between multiple versions of dbt in dedicated Python virtual environments.
        """,
        parents=[command_common_args_parser],
        epilog="Run a sub-command with the `--help` option to see help for that sub-command."
    )

    subparsers = parser.add_subparsers(dest='subcommand', title="Sub-commands")
    dbtenv.versions.build_versions_args_parser(subparsers, subcommand_common_args_parser)
    dbtenv.install.build_install_args_parser(subparsers, subcommand_common_args_parser)
    dbtenv.version.build_version_args_parser(subparsers, subcommand_common_args_parser)
    dbtenv.which.build_which_args_parser(subparsers, subcommand_common_args_parser)
    dbtenv.execute.build_execute_args_parser(subparsers, subcommand_common_args_parser)
    dbtenv.uninstall.build_uninstall_args_parser(subparsers, subcommand_common_args_parser)

    return parser


def _build_common_args_parser(dest_prefix: str = '') -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--python',
        dest=f'{dest_prefix}python',
        metavar='<path>',
        help=f"""
            Path to the Python executable to use when installing dbt.
            The default is the Python executable used to install dbtenv, but that can be overridden by setting a
            {dbtenv.PYTHON_VAR} environment variable.
        """
    )
    parser.add_argument(
        '--auto-install',
        dest=f'{dest_prefix}auto_install',
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
        dest=f'{dest_prefix}debug',
        action='store_const',
        const=True,
        help=f"""
            Output debug information as dbtenv runs.
            The default is to not output debug information, but that can be overridden by setting a {dbtenv.DEBUG_VAR}
            environment variable.
        """
    )
    return parser


def main(args: List[str] = None) -> None:
    try:
        if args is None:
            args = sys.argv[1:]

        args_parser = build_args_parser()
        parsed_args = args_parser.parse_args(args)
        subcommand = parsed_args.subcommand

        debug = parsed_args.debug or (subcommand and parsed_args.subcommand_debug)
        if debug:
            dbtenv.set_debug(debug)

        python = parsed_args.python or (subcommand and parsed_args.subcommand_python)
        if python:
            dbtenv.set_python(python)

        auto_install = parsed_args.auto_install or (subcommand and parsed_args.subcommand_auto_install)
        if auto_install:
            dbtenv.set_auto_install(auto_install)

        logger.debug(f"Parsed arguments = {parsed_args}")

        if not subcommand:
            args_parser.print_help()
            sys.exit(EXIT_CODES.failure)

        if subcommand == 'versions':
            dbtenv.versions.run_versions_command(parsed_args)
        elif subcommand == 'install':
            dbtenv.install.run_install_command(parsed_args)
        elif subcommand == 'version':
            dbtenv.version.run_version_command(parsed_args)
        elif subcommand == 'which':
            dbtenv.which.run_which_command(parsed_args)
        elif subcommand in ('execute', 'exec'):
            dbtenv.execute.run_execute_command(parsed_args)
        elif subcommand == 'uninstall':
            dbtenv.uninstall.run_uninstall_command(parsed_args)
        else:
            raise dbtenv.DbtenvRuntimeError(f"Unknown sub-command `{subcommand}`.")
    except dbtenv.DbtenvRuntimeError as error:
        logger.error(error)
        sys.exit(EXIT_CODES.failure)

    sys.exit(EXIT_CODES.success)
