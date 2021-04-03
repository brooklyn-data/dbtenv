import argparse
from typing import List

import dbtenv
from dbtenv import Args, DbtenvError, Environment, Installer, Subcommand, Version
import dbtenv.homebrew
import dbtenv.venv
import dbtenv.which


logger = dbtenv.LOGGER


class InstallSubcommand(Subcommand):
    """
    Install the specified dbt version from the Python Package Index or the specified package location using pip,
    or optionally using Homebrew on Mac or Linux.
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
            'dbt_version',
            type=Version,
            metavar='<dbt_version>',
            help="Exact version of dbt to install."
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
        if self.env.primary_installer == Installer.PIP:
            venv_dbt = dbtenv.venv.VenvDbt(self.env, args.dbt_version)
            venv_dbt.install(force=args.force, package_location=args.package_location, editable=args.editable)
        elif self.env.primary_installer == Installer.HOMEBREW:
            homebrew_dbt = dbtenv.homebrew.HomebrewDbt(self.env, args.dbt_version)
            homebrew_dbt.install(force=args.force)
        else:
            raise DbtenvError(f"Unknown installer `{self.env.primary_installer}`.")


def install_dbt(env: Environment, version: Version) -> None:
    if env.primary_installer == Installer.PIP:
        dbtenv.venv.VenvDbt(env, version).install()
    elif env.primary_installer == Installer.HOMEBREW:
        dbtenv.homebrew.HomebrewDbt(env, version).install()
    else:
        raise DbtenvError(f"Unknown installer `{env.primary_installer}`.")


def ensure_dbt_is_installed(env: Environment, version: Version) -> None:
    if not dbtenv.which.try_get_dbt(env, version):
        if env.auto_install:
            install_dbt(env, version)
        else:
            raise DbtenvError(f"No dbt {version} installation found and auto-install is not enabled.")
