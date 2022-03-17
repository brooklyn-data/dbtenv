# Standard library
import argparse
from typing import List

# Local
import dbtenv
from dbtenv import Args, DbtenvError, Subcommand, Version
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
            'dbt_pip_specifier',
            type=str,
            metavar='<dbt_version>',
            help="dbt package (adapter) to uninstall, in pip specifier format (e.g. dbt-snowflake==1.0.1)."
        )

    def execute(self, args: Args) -> None:
        version = Version(pip_specifier=args.dbt_pip_specifier)
        attempted_uninstalls = 0

        pip_dbt = dbtenv.pip.PipDbt(self.env, version)
        if pip_dbt.is_installed():
            pip_dbt.uninstall(force=args.force)
            attempted_uninstalls += 1

        if attempted_uninstalls == 0:
            raise DbtenvError(f"No {version} installation found.")
