# Standard library
import argparse
from typing import List

# Local
import dbtenv
from dbtenv import Args, DbtenvError, Environment, Installer, Subcommand, Version
import dbtenv.pip
import dbtenv.version
import dbtenv.which


logger = dbtenv.LOGGER


class InstallSubcommand(Subcommand):
    """
    Install the specified dbt version from the Python Package Index or the specified package location using pip.
    """

    name = 'install'

    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            parents=parent_parsers,
            description=self.__doc__,
            help=self.__doc__
        )
        parser.add_argument(
            '-f',
            '--force',
            action='store_true',
            help="Install even if the dbt version appears to already be installed."
        )
        parser.add_argument(
            'dbt_pip_specifier',
            nargs='?',
            type=str,
            metavar='<dbt_pip_specifier>',
            help="""
                dbt package (adapter) to install, in pip specifier format (e.g. dbt-snowflake==1.0.1).
                If not specified, dbtenv will attempt to identify the required adapter and version from the environment.
            """
        )
        parser.add_argument(
            'package_location',
            nargs='?',
            metavar='<package_location>',
            help="""
                When installing using pip, the optional location of the dbt package to install, which can be a
                pip-compatible version control project URL, local project path, or archive URL/path.
                If not specified, dbt will be installed from the Python Package Index.
            """
        )
        parser.add_argument(
            '-e',
            '--editable',
            action='store_true',
            help="""
                When installing a dbt package from a version control project URL or local project path using pip,
                install it in "editable" mode.
            """
        )

    def execute(self, args: Args) -> None:
        if args.dbt_pip_specifier:
            dbt_pip_specifier = args.dbt_pip_specifier
        else:
            version = dbtenv.version.get_version(self.env)
            logger.info(f"Using {version} ({version.source_description}).")

        version = Version(pip_specifier=dbt_pip_specifier)

        pip_dbt = dbtenv.pip.PipDbt(self.env, version)
        pip_dbt.install(force=args.force, package_location=args.package_location, editable=args.editable)


def install_dbt(env: Environment, version: Version) -> None:
    dbtenv.pip.PipDbt(env, version).install()


def ensure_dbt_is_installed(env: Environment, version: Version) -> None:
    if not dbtenv.which.try_get_dbt(env, version):
        if env.auto_install:
            install_dbt(env, version)
        else:
            raise DbtenvError(f"No dbt {version} installation found and auto-install is not enabled.")
