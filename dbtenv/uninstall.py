import argparse
from typing import List

import dbtenv
from dbtenv import Args, DbtenvError, Installer, Subcommand, Version
import dbtenv.homebrew
import dbtenv.venv


logger = dbtenv.LOGGER


class UninstallSubcommand(Subcommand):
    """Uninstall the specified dbt version."""

    name = 'uninstall'

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
            help="Uninstall without prompting for confirmation."
        )
        parser.add_argument(
            'dbt_version',
            type=Version,
            metavar='<dbt_version>',
            help="Exact version of dbt to uninstall."
        )

    def execute(self, args: Args) -> None:
        uninstall_all           = not self.env.installer
        only_uninstall_venv     = self.env.installer == Installer.PIP
        only_uninstall_homebrew = self.env.installer == Installer.HOMEBREW
        uninstall_venv          = uninstall_all or only_uninstall_venv
        uninstall_homebrew      = (uninstall_all or only_uninstall_homebrew) and self.env.homebrew_installed

        attempted_uninstalls = 0

        if uninstall_venv:
            venv_dbt = dbtenv.venv.VenvDbt(self.env, args.dbt_version)
            if venv_dbt.is_installed():
                venv_dbt.uninstall(force=args.force)
                attempted_uninstalls += 1

        if uninstall_homebrew:
            homebrew_dbt = dbtenv.homebrew.HomebrewDbt(self.env, args.dbt_version)
            if homebrew_dbt.is_installed():
                homebrew_dbt.uninstall(force=args.force)
                attempted_uninstalls += 1

        if attempted_uninstalls == 0:
            raise DbtenvError(f"No dbt {args.dbt_version} installation found.")
