# Standard library
import argparse
from typing import List, Set, Optional

# Local
import dbtenv
from dbtenv import Args, DbtenvError, Environment, Installer, Subcommand, Version
import dbtenv.pip
import dbtenv.version


logger = dbtenv.LOGGER


class VersionsSubcommand(Subcommand):
    """Show the dbt versions that are available to be installed, or that are installed."""

    name = 'versions'

    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            parents=parent_parsers,
            description=self.__doc__,
            help=self.__doc__
        )
        parser.add_argument(
            '-i',
            '--installed',
            action='store_true',
            help=f"Only show the installed dbt versions."
        )

    def execute(self, args: Args) -> None:
        installed_versions = get_installed_versions(self.env)

        distinct_versions = installed_versions.copy()
        if not args.installed:
            distinct_versions.update(get_installable_versions(self.env))

        versions = list(distinct_versions)
        versions.sort()

        if versions:
            active_version = dbtenv.version.get_version(self.env)
            logger.info("+ = installed, * = active")
            for version in versions:
                line = "+ " if version in installed_versions else "  "
                line += "* " if active_version and version == active_version else "  "
                line += version.pip_specifier
                if active_version and version == active_version:
                    line += f"  ({active_version.source_description})"
                print(line)
        else:
            logger.info(f"No dbt installations found.")


def get_installed_versions(env: Environment, adapter_type: Optional[str] = None) -> Set[Version]:
    installed_versions = set()
    installed_versions.update(dbtenv.pip.get_installed_pip_dbt_versions(env, adapter_type=adapter_type))
    return installed_versions


def get_installable_versions(env: Environment, adapter_type: Optional[str] = None) -> List[Version]:
    if adapter_type:
        return dbtenv.pip.get_pypi_package_versions(adapter_type)
    else:
        return dbtenv.pip.get_pypi_all_dbt_package_versions()
