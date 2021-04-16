# Standard library
import argparse
from typing import List

# Local
import dbtenv
from dbtenv import Args, DbtenvError, Subcommand, Version
import dbtenv.homebrew
import dbtenv.pip


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
        attempted_uninstalls = 0

        if self.env.use_pip:
            pip_dbt = dbtenv.pip.PipDbt(self.env, args.dbt_version)
            if pip_dbt.is_installed():
                pip_dbt.uninstall(force=args.force)
                attempted_uninstalls += 1

        if self.env.use_homebrew:
            homebrew_dbt = dbtenv.homebrew.HomebrewDbt(self.env, args.dbt_version)
            if homebrew_dbt.is_installed():
                homebrew_dbt.uninstall(force=args.force)
                attempted_uninstalls += 1

        if attempted_uninstalls == 0:
            raise DbtenvError(f"No dbt {args.dbt_version} installation found.")
