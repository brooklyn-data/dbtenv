import argparse
from enum import IntEnum
import sys
from typing import List

import dbtenv
import dbtenv.execute
import dbtenv.install
import dbtenv.uninstall
import dbtenv.version
import dbtenv.versions
import dbtenv.which


logger = dbtenv.LOGGER


class ExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INTERRUPTED = 2


def build_args_parser() -> argparse.ArgumentParser:
    common_command_args_parser    = _build_common_args_parser()
    common_subcommand_args_parser = _build_common_args_parser(dest_prefix='subcommand_')

    parser = argparse.ArgumentParser(
        description=f"""
            Lets you easily install and switch between multiple versions of dbt using pip with Python virtual environments,
            or optionally using Homebrew on Mac or Linux.
            Any dbt version-specific Python virtual environments are created under `{dbtenv.VENVS_DIRECTORY}`.
            The dbt version to use can be configured globally in a `{dbtenv.GLOBAL_VERSION_FILE}` file, locally within
            specific directories using `{dbtenv.LOCAL_VERSION_FILE}` files, or in your shell using a
            {dbtenv.DBT_VERSION_VAR} environment variable.
        """,
        parents=[common_command_args_parser],
        epilog="Run a sub-command with the --help option to see help for that sub-command."
    )

    common_install_args_parser = argparse.ArgumentParser(add_help=False)
    common_install_args_parser.add_argument(
        '--python',
        metavar='<path>',
        help=f"""
            Path to the Python executable to use when installing using pip.
            The default is the Python executable used to install dbtenv, but that can be overridden by setting a
            {dbtenv.PYTHON_VAR} environment variable.
        """
    )
    common_install_args_parser.add_argument(
        '--simulate-release-date',
        action='store_const',
        const=True,
        help=f"""
            When installing using pip, only install packages that were available on the date the dbt version was released.
            The default is to not simulate the dbt release date, but that can be overridden by setting a
            {dbtenv.SIMULATE_RELEASE_DATE_VAR} environment variable.
        """
    )

    auto_install_arg_parser = argparse.ArgumentParser(add_help=False)
    auto_install_arg_parser.add_argument(
        '--auto-install',
        action='store_const',
        const=True,
        help=f"""
            Automatically install a specified dbt version if it isn't already installed.
            The default is to not auto-install, but that can be overridden by setting a {dbtenv.AUTO_INSTALL_VAR}
            environment variable.
        """
    )

    subparsers = parser.add_subparsers(dest='subcommand', title="Sub-commands")
    dbtenv.versions.build_versions_args_parser(subparsers, [common_subcommand_args_parser])
    dbtenv.install.build_install_args_parser(subparsers, [common_subcommand_args_parser, common_install_args_parser])
    dbtenv.version.build_version_args_parser(subparsers, [common_subcommand_args_parser, common_install_args_parser, auto_install_arg_parser])
    dbtenv.which.build_which_args_parser(subparsers, [common_subcommand_args_parser])
    dbtenv.execute.build_execute_args_parser(subparsers, [common_subcommand_args_parser, common_install_args_parser, auto_install_arg_parser])
    dbtenv.uninstall.build_uninstall_args_parser(subparsers, [common_subcommand_args_parser])

    return parser


def _build_common_args_parser(dest_prefix: str = '') -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
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
    if dbtenv.ENV.homebrew_installed:
        parser.add_argument(
            '--installer',
            dest=f'{dest_prefix}installer',
            type=dbtenv.Installer,
            choices=dbtenv.Installer,
            help=f"""
                Which installer to use.
                The default is pip, but that can be overridden by setting a {dbtenv.DEFAULT_INSTALLER_VAR} environment variable.
            """
        )
    return parser


def main(args: List[str] = None) -> None:
    try:
        if args is None:
            args = sys.argv[1:]

        logger.debug(f"Arguments = {args}")

        parsed_args = dbtenv.Args()
        args_parser = build_args_parser()
        args_parser.parse_args(args, namespace=parsed_args)

        debug = parsed_args.debug or parsed_args.get('subcommand_debug')
        if debug:
            dbtenv.ENV.debug = debug

        installer = parsed_args.get('installer') or parsed_args.get('subcommand_installer')
        if installer:
            dbtenv.ENV.installer = installer

        python = parsed_args.get('python')
        if python:
            dbtenv.ENV.python = python

        auto_install = parsed_args.get('auto_install')
        if auto_install:
            dbtenv.ENV.auto_install = auto_install

        simulate_release_date = parsed_args.get('simulate_release_date')
        if simulate_release_date:
            dbtenv.ENV.simulate_release_date = simulate_release_date

        logger.debug(f"Parsed arguments = {parsed_args}")

        subcommand = parsed_args.subcommand
        if not subcommand:
            args_parser.print_help()
            sys.exit(ExitCode.FAILURE)

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
            raise dbtenv.DbtenvError(f"Unknown sub-command `{subcommand}`.")
    except dbtenv.DbtenvError as error:
        logger.error(error)
        sys.exit(ExitCode.FAILURE)
    except dbtenv.DbtError as dbt_error:
        logger.debug(dbt_error)
        sys.exit(dbt_error.exit_code)
    except KeyboardInterrupt:
        logger.debug("Received keyboard interrupt.")
        sys.exit(ExitCode.INTERRUPTED)

    sys.exit(ExitCode.SUCCESS)
