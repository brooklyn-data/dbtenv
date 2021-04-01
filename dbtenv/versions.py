import argparse
from typing import List, Set

import dbtenv
import dbtenv.homebrew
import dbtenv.pypi
import dbtenv.venv
import dbtenv.version


logger = dbtenv.LOGGER


class VersionsSubcommand(dbtenv.Subcommand):
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

    def execute(self, args: dbtenv.Args) -> None:
        primary_installer = self.env.installer or self.env.default_installer
        use_any_installer = not self.env.installer
        only_use_venv     = self.env.installer == dbtenv.Installer.PIP
        only_use_homebrew = self.env.installer == dbtenv.Installer.HOMEBREW
        use_venv          = use_any_installer or only_use_venv
        use_homebrew      = (use_any_installer or only_use_homebrew) and self.env.homebrew_installed

        installed_versions: Set[dbtenv.Version] = set()
        if use_venv:
            installed_versions.update(dbtenv.venv.get_installed_venv_dbt_versions(self.env))
        if use_homebrew:
            installed_versions.update(dbtenv.homebrew.get_installed_homebrew_dbt_versions(self.env))

        distinct_versions = installed_versions.copy()
        if not args.installed:
            if primary_installer == dbtenv.Installer.PIP:
                distinct_versions.update(dbtenv.pypi.get_pypi_dbt_versions())
            elif primary_installer == dbtenv.Installer.HOMEBREW:
                distinct_versions.update(dbtenv.homebrew.get_homebrew_dbt_versions())
            else:
                raise dbtenv.DbtenvError(f"Unknown installer `{primary_installer}`.")

        versions = list(distinct_versions)
        versions.sort()

        if versions:
            active_version = dbtenv.version.try_get_version(self.env)
            logger.info("+ = installed, * = active")
            for version in versions:
                line = "+ " if version in installed_versions else "  "
                line += "* " if version == active_version else "  "
                line += version.get_installer_version(primary_installer)
                if version == active_version:
                    line += f"  (set by {active_version.source})"
                print(line)
        else:
            logger.info(f"No dbt installations found.")
