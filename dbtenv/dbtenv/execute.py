# Standard library
import argparse
import re
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
            dest='dbt_version_specifier',
            type=str,
            metavar='<dbt_version_specifier>',
            help="""
                dbt version (e.g. 1.0.0) or full pip specifier to use (e.g. dbt-snowflake==1.0.0).
                dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.
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
        arg_target_name = None
        for i, arg in enumerate(args.dbt_args):
            if arg == "--target":
                arg_target_name = args.dbt_args[i+1]
                break

        adapter_type = dbtenv.version.try_get_project_adapter_type(self.env.project_file, target_name=arg_target_name)
        if args.dbt_version_specifier:
            if bool(re.search(r"^(dbt-.+)==(.+)$", args.dbt_version_specifier)):
                version = Version(pip_specifier=args.dbt_version_specifier, source_description="specified using --dbt arg")
            elif bool(re.search(r"^[0-9\.]+[a-z0-9]*$", args.dbt_version_specifier)):
                if not adapter_type:
                    logger.info("Could not determine adapter type as no default target is set for the current project in profiles.yml.")
                    return
                version = Version(adapter_type=adapter_type, version=args.dbt_version_specifier, source_description="adapter type automatically detected, version specified using --dbt arg")
            else:
                logger.info("The argument passed to --dbt didn't match a dbt version (e.g. 1.0.0) or full pip specifier (e.g. dbt-snowflake==1.0.0).")
                return
        else:
            version = dbtenv.version.get_version(self.env, adapter_type=adapter_type)

        if not version:
            return

        logger.info(f"Using {version} ({version.source_description}).")

        dbt = dbtenv.which.try_get_dbt(self.env, version)
        if not dbt:
            if self.env.auto_install:
                dbtenv.install.install_dbt(self.env, version)
                dbt = dbtenv.which.get_dbt(self.env, version)
            else:
                raise DbtenvError(f"No dbt {version} installation found and auto-install is not enabled.")

        dbt.execute(args.dbt_args)
