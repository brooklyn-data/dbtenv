# Standard library
import argparse
from typing import List, Optional

# Local
import dbtenv
from dbtenv import Args, Dbt, DbtenvError, Environment, Installer, Subcommand, Version
import dbtenv.pip
import dbtenv.version


logger = dbtenv.LOGGER


class WhichSubcommand(Subcommand):
    """
    Show the full path to the executable of the specified dbt version or the dbt version automatically detected from
    the environment.
    """

    name = 'which'

    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            parents=parent_parsers,
            description=f"""
                Show the full path to the executable of the specified dbt version or the dbt version automatically
                detected from the environment based on the global `{dbtenv.GLOBAL_VERSION_FILE}` file, local
                `{dbtenv.LOCAL_VERSION_FILE}` files, or {dbtenv.DBT_VERSION_VAR} environment variable.
            """,
            help=self.__doc__
        )
        parser.add_argument(
            'dbt_version',
            nargs='?',
            type=str,
            metavar='<dbt_version>',
            help="""
                Exact version of dbt to show.
                If not specified, the dbt version will be automatically detected from the environment.
            """
        )

    def execute(self, args: Args) -> None:
        adapter_type = dbtenv.version.try_get_project_adapter_type(self.env.project_file)

        if args.dbt_version:
            version = Version(adapter_type=adapter_type, dbt_version=args.dbt_version)
        else:
            version = dbtenv.version.get_version(self.env, adapter_type=adapter_type)

        if version:
            logger.info(f"Using {version} ({version.source_description}).")
            print(get_dbt(self.env, version).get_executable())


def get_dbt(env: Environment, version: Version) -> Dbt:
    error = DbtenvError(f"No dbt {version} executable found.")

    pip_dbt = dbtenv.pip.PipDbt(env, version)
    pip_dbt.get_executable()  # Raises an appropriate error if it's not installed.

    if pip_dbt and pip_dbt.is_installed():
        return pip_dbt
    else:
        raise error


def try_get_dbt(env: Environment, version: Version) -> Optional[Dbt]:
    try:
        return get_dbt(env, version)
    except Exception as error:
        logger.debug(f"Error getting dbt:  {error}")
        return None
