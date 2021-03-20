import argparse
from typing import List

import dbtenv
import dbtenv.install
import dbtenv.which


logger = dbtenv.LOGGER


class ExecuteSubcommand(dbtenv.Subcommand):
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
            type=dbtenv.Version,
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

    def execute(self, args: dbtenv.Args) -> None:
        if args.dbt_version:
            version = args.dbt_version
        else:
            version, version_source = self.env.try_get_version_and_source()
            if version:
                logger.info(f"Using dbt {version} (set by {version_source}).")
            else:
                raise dbtenv.DbtenvError("No dbt version has been set globally, for the local directory, or for the current shell.")

        dbt = dbtenv.which.try_get_dbt(self.env, version)
        if not dbt:
            if self.env.auto_install:
                dbtenv.install.install_dbt(self.env, version)
                dbt = dbtenv.which.get_dbt(self.env, version)
            else:
                raise dbtenv.DbtenvError(f"No dbt {version} installation found and auto-install is not enabled.")

        dbt.execute(args.dbt_args)
