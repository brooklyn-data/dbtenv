import argparse
from typing import List

import dbtenv
import dbtenv.install


logger = dbtenv.LOGGER


class VersionSubcommand(dbtenv.Subcommand):
    """
    Show the dbt version automatically detected from the environment, or show/set the dbt version globally,
    for the local directory, or for the current shell.
    """

    name = 'version'

    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            parents=parent_parsers,
            description=self.__doc__,
            help=self.__doc__
        )
        scope_group = parser.add_mutually_exclusive_group()
        scope_group.add_argument(
            '--global',
            dest='global_dbt_version',
            nargs='?',
            type=dbtenv.Version,
            const='',
            metavar='<dbt_version>',
            help=f"Show/set the dbt version globally using the `{dbtenv.GLOBAL_VERSION_FILE}` file."
        )
        scope_group.add_argument(
            '--local',
            dest='local_dbt_version',
            nargs='?',
            type=dbtenv.Version,
            const='',
            metavar='<dbt_version>',
            help=f"Show/set the dbt version for the local directory using `{dbtenv.LOCAL_VERSION_FILE}` files."
        )
        scope_group.add_argument(
            '--shell',
            dest='shell_dbt_version',
            action='store_const',
            const=True,
            help=f"Show the dbt version set for the current shell using a {dbtenv.DBT_VERSION_VAR} environment variable."
        )

    def execute(self, args: dbtenv.Args) -> None:
        if args.global_dbt_version is not None:
            if args.global_dbt_version != '':
                dbtenv.install.ensure_dbt_is_installed(self.env, args.global_dbt_version)
                self.env.set_global_version(args.global_dbt_version)
            else:
                global_version = self.env.try_get_global_version()
                if global_version:
                    print(global_version)
                else:
                    logger.info(f"No global dbt version has been set using the `{dbtenv.GLOBAL_VERSION_FILE}` file.")
        elif args.local_dbt_version is not None:
            if args.local_dbt_version != '':
                dbtenv.install.ensure_dbt_is_installed(self.env, args.local_dbt_version)
                self.env.set_local_version(args.local_dbt_version)
            else:
                local_version, version_file = self.env.try_get_local_version_and_source()
                if local_version:
                    print(f"{local_version}  (set by `{version_file}`)")
                else:
                    logger.info(f"No local dbt version has been set for `{self.env.working_directory}` using `{dbtenv.LOCAL_VERSION_FILE}` files.")
        elif args.shell_dbt_version is not None:
            shell_version = self.env.try_get_shell_version()
            if shell_version:
                print(shell_version)
            else:
                logger.info(f"No dbt version has been set for the current shell using a {dbtenv.DBT_VERSION_VAR} environment variable.")
        else:
            version, source = self.env.try_get_version_and_source()
            if version:
                print(f"{version}  (set by {source})")
            else:
                logger.info("No dbt version has been set globally, for the local directory, or for the current shell.")
