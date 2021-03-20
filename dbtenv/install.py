import argparse
from typing import List

import dbtenv
import dbtenv.homebrew
import dbtenv.venv
import dbtenv.which


logger = dbtenv.LOGGER


class InstallSubcommand(dbtenv.Subcommand):
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
            type=dbtenv.Version,
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

    def execute(self, args: dbtenv.Args) -> None:
        installer = self.env.installer or self.env.default_installer
        if installer == dbtenv.Installer.PIP:
            venv_dbt = dbtenv.venv.VenvDbt(self.env, args.dbt_version)
            venv_dbt.install(force=args.force, package_location=args.package_location, editable=args.editable)
        elif installer == dbtenv.Installer.HOMEBREW:
            homebrew_dbt = dbtenv.homebrew.HomebrewDbt(self.env, args.dbt_version)
            homebrew_dbt.install(force=args.force)
        else:
            raise dbtenv.DbtenvError(f"Unknown installer `{installer}`.")


def install_dbt(env: dbtenv.Environment, version: dbtenv.Version) -> None:
    installer = env.installer or env.default_installer
    if installer == dbtenv.Installer.PIP:
        dbtenv.venv.VenvDbt(env, version).install()
    elif installer == dbtenv.Installer.HOMEBREW:
        dbtenv.homebrew.HomebrewDbt(env, version).install()
    else:
        raise dbtenv.DbtenvError(f"Unknown installer `{installer}`.")


def ensure_dbt_is_installed(env: dbtenv.Environment, version: dbtenv.Version) -> None:
    if not dbtenv.which.try_get_dbt(env, version):
        if env.auto_install:
            install_dbt(env, version)
        else:
            raise dbtenv.DbtenvError(f"No dbt {version} installation found and auto-install is not enabled.")
