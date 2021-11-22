# Standard library
import argparse
from typing import List

# Local
import dbtenv
from dbtenv import Args, DbtenvError, Subcommand, Version
import dbtenv.install
import dbtenv.version
import dbtenv.which


logger = dbtenv.LOGGER


class ExecuteSubcommand(Subcommand):
    """Execute a dbt command using the specified dbt version or the dbt version automatically detected from the environment."""

    name = 'execute'
    aliases = ['exec']

    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            aliases=self.aliases,
            parents=parent_parsers,
            description=f"""
                Execute a dbt command using the specified dbt version or the dbt version automatically detected from the
                environment based on the global `{dbtenv.GLOBAL_VERSION_FILE}` file, local `{dbtenv.LOCAL_VERSION_FILE}` files,
                or {dbtenv.DBT_VERSION_VAR} environment variable.
            """,
            help=self.__doc__
        )
        parser.add_argument(
            '--dbt',
            dest='dbt_version',
            type=Version,
            metavar='<dbt_version>',
            help="""
                Exact version of dbt to execute.
                If not specified, the dbt version will be automatically detected from the environment.
            """
        )
        parser.add_argument(
            'dbt_args',
            nargs='*',
            metavar='<dbt_args>',
            help="""
                Arguments to pass to dbt.
                It's highly recommended to specify ` -- ` (two dashes with spaces on both sides) before this list of
                arguments so dbtenv doesn't try to interpret them.
            """
        )

    def execute(self, args: Args) -> None:
        if args.dbt_version:
            version = args.dbt_version
        else:
            version = dbtenv.version.get_version(self.env)
            logger.info(f"Using dbt {version} ({version.source_description}).")

        dbt = dbtenv.which.try_get_dbt(self.env, version)
        if not dbt:
            if self.env.auto_install:
                dbtenv.install.install_dbt(self.env, version)
                dbt = dbtenv.which.get_dbt(self.env, version)
            else:
                raise DbtenvError(f"No dbt {version} installation found and auto-install is not enabled.")

        dbt.execute(args.dbt_args)
