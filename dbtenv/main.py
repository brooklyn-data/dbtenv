# Standard library
import argparse
from enum import IntEnum
import sys
import importlib.metadata
from typing import List

# Local
import dbtenv
from dbtenv import Args, DbtenvError, DbtError, Environment, Installer
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


def build_root_args_parser(env: Environment) -> argparse.ArgumentParser:
    common_args_parser = build_common_args_parser(env)
    root_args_parser = argparse.ArgumentParser(
        description=f"""
            Lets you easily install and run multiple versions of dbt using pip with Python virtual environments.
            Any dbt version-specific Python virtual environments are created under `{dbtenv.DEFAULT_VENVS_DIRECTORY}` by default,
            but that can be configured using {dbtenv.VENVS_DIRECTORY_VAR} environment variable.
            The dbt version to use can be configured in your shell using a {dbtenv.DBT_VERSION_VAR} environment variable,
            in dbt projects using the `require-dbt-version` configuration, locally within specific directories using
            `{dbtenv.LOCAL_VERSION_FILE}` files, or globally in a `{dbtenv.GLOBAL_VERSION_FILE}` file.
        """,
        parents=[common_args_parser],
        epilog="Run a sub-command with the --help option to see help for that sub-command."
    )
    root_args_parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {importlib.metadata.version("dbtenv")}',
        help="Show %(prog)s version and exit."
    )
    return root_args_parser


def build_common_args_parser(env: Environment, dest_prefix: str = '') -> argparse.ArgumentParser:
    common_args_parser = argparse.ArgumentParser(add_help=False)
    common_args_parser.add_argument(
        '--debug',
        dest=f'{dest_prefix}debug',
        action='store_const',
        const=True,
        help=f"""
            Output debug information as dbtenv runs.
            This can also be enabled by setting a {dbtenv.DEBUG_VAR} environment variable.
        """
    )
    common_args_parser.add_argument(
        '--quiet',
        dest=f'{dest_prefix}quiet',
        action='store_const',
        const=True,
        help=f"""
            Don't output any nonessential information as dbtenv runs.
            This can also be enabled by setting a {dbtenv.QUIET_VAR} environment variable.
            Note that if outputting debug information has been enabled this setting will have no effect.
        """
    )
    return common_args_parser


def build_common_install_args_parser(env: Environment) -> argparse.ArgumentParser:
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
    return common_install_args_parser


def main(args: List[str] = None) -> None:
    try:
        if args is None:
            args = sys.argv[1:]

        logger.debug(f"Arguments = {args}")

        env = Environment()

        versions_subcommand = dbtenv.versions.VersionsSubcommand(env)
        install_subcommand = dbtenv.install.InstallSubcommand(env)
        version_subcommand = dbtenv.version.VersionSubcommand(env)
        which_subcommand = dbtenv.which.WhichSubcommand(env)
        execute_subcommand = dbtenv.execute.ExecuteSubcommand(env)
        uninstall_subcommand = dbtenv.uninstall.UninstallSubcommand(env)

        args_parser = build_root_args_parser(env)
        subparsers = args_parser.add_subparsers(dest='subcommand', title="Sub-commands")
        common_subcommand_args_parser = build_common_args_parser(env, dest_prefix='subcommand_')
        common_install_args_parser = build_common_install_args_parser(env)
        versions_subcommand.add_args_parser(subparsers, [common_subcommand_args_parser])
        install_subcommand.add_args_parser(subparsers, [common_subcommand_args_parser, common_install_args_parser])
        version_subcommand.add_args_parser(subparsers, [common_subcommand_args_parser, common_install_args_parser])
        which_subcommand.add_args_parser(subparsers, [common_subcommand_args_parser])
        execute_subcommand.add_args_parser(subparsers, [common_subcommand_args_parser, common_install_args_parser])
        uninstall_subcommand.add_args_parser(subparsers, [common_subcommand_args_parser])

        parsed_args = Args()
        args_parser.parse_args(args, namespace=parsed_args)

        debug = parsed_args.debug or parsed_args.get('subcommand_debug')
        if debug:
            env.debug = debug

        logger.debug(f"Parsed arguments = {parsed_args}")

        quiet = parsed_args.quiet or parsed_args.get('subcommand_quiet')
        if quiet:
            env.quiet = quiet

        installer = parsed_args.get('installer') or parsed_args.get('subcommand_installer')
        if installer:
            env.installer = installer

        python = parsed_args.get('python')
        if python:
            env.python = python

        simulate_release_date = parsed_args.get('simulate_release_date')
        if simulate_release_date:
            env.simulate_release_date = simulate_release_date

        subcommand = parsed_args.subcommand
        if not subcommand:
            args_parser.print_help()
            sys.exit(ExitCode.FAILURE)

        if subcommand == versions_subcommand.name:
            versions_subcommand.execute(parsed_args)
        elif subcommand == install_subcommand.name:
            install_subcommand.execute(parsed_args)
        elif subcommand == version_subcommand.name:
            version_subcommand.execute(parsed_args)
        elif subcommand == which_subcommand.name:
            which_subcommand.execute(parsed_args)
        elif subcommand == execute_subcommand.name or subcommand in execute_subcommand.aliases:
            execute_subcommand.execute(parsed_args)
        elif subcommand == uninstall_subcommand.name:
            uninstall_subcommand.execute(parsed_args)
        else:
            raise DbtenvError(f"Unknown sub-command `{subcommand}`.")
    except DbtenvError as error:
        logger.error(error)
        sys.exit(ExitCode.FAILURE)
    except DbtError as dbt_error:
        logger.debug(dbt_error)
        sys.exit(dbt_error.exit_code)
    except KeyboardInterrupt:
        logger.debug("Received keyboard interrupt.")
        sys.exit(ExitCode.INTERRUPTED)

    sys.exit(ExitCode.SUCCESS)
