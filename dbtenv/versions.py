import argparse
import glob
import json
import os
import re
import subprocess
from typing import List, Set

import dbtenv
import dbtenv.install
import dbtenv.version
import dbtenv.which


logger = dbtenv.LOGGER


def build_versions_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    description = "Show the dbt versions that are available to be installed, or that are installed."
    parser = subparsers.add_parser(
        'versions',
        parents=parent_parsers,
        description=description,
        help=description
    )
    parser.add_argument(
        '-i',
        '--installed',
        action='store_true',
        help=f"Only show the installed dbt versions."
    )


def run_versions_command(args: dbtenv.Args) -> None:
    primary_installer = dbtenv.ENV.installer or dbtenv.ENV.default_installer
    use_any_installer = not dbtenv.ENV.installer
    only_use_venv     = dbtenv.ENV.installer == dbtenv.Installer.PIP
    only_use_homebrew = dbtenv.ENV.installer == dbtenv.Installer.HOMEBREW
    use_venv          = use_any_installer or only_use_venv
    use_homebrew      = (use_any_installer or only_use_homebrew) and dbtenv.ENV.homebrew_installed

    installed_versions: Set[dbtenv.Version] = set()
    if use_venv:
        installed_versions.update(get_installed_venv_dbt_versions())
    if use_homebrew:
        installed_versions.update(get_installed_homebrew_dbt_versions())

    distinct_versions = installed_versions.copy()
    if not args.installed:
        if primary_installer == dbtenv.Installer.PIP:
            distinct_versions.update(get_pypi_dbt_versions())
        elif primary_installer == dbtenv.Installer.HOMEBREW:
            distinct_versions.update(get_homebrew_dbt_versions())
        else:
            raise dbtenv.DbtenvError(f"Unknown installer `{primary_installer}`.")

    versions = list(distinct_versions)
    versions.sort()

    if versions:
        active_version, active_version_source = dbtenv.version.get_version(os.getcwd())
        logger.info("+ = installed, * = active")
        for version in versions:
            line = "+ " if version in installed_versions else "  "
            line += "* " if version == active_version else "  "
            line += version.get_installer_version(primary_installer)
            if version == active_version:
                line += f"  (set by {active_version_source})"
            print(line)
    else:
        logger.info(f"No dbt installations found.")


def get_installed_venv_dbt_versions() -> List[dbtenv.Version]:
    possible_versions = (dbtenv.Version(entry.name) for entry in os.scandir(dbtenv.ENV.venvs_directory) if os.path.isdir(entry))
    return [version for version in possible_versions if dbtenv.which.try_get_venv_dbt(version)]


def get_installed_homebrew_dbt_versions() -> List[dbtenv.Version]:
    keg_dir_pattern = os.path.join(dbtenv.ENV.homebrew_cellar_directory, 'dbt@*') + os.path.sep
    installed_formulae = [os.path.basename(os.path.dirname(keg_dir)) for keg_dir in glob.glob(keg_dir_pattern)]
    return [dbtenv.Version(re.sub(r'^dbt@', '', formula)) for formula in installed_formulae]


def get_pypi_dbt_versions() -> List[dbtenv.Version]:
    package_metadata = dbtenv.install.get_pypi_package_metadata('dbt')
    possible_versions = ((dbtenv.Version(version), files) for version, files in package_metadata['releases'].items())
    return [version for version, files in possible_versions if any(not file['yanked'] for file in files)]


def get_homebrew_dbt_versions() -> List[dbtenv.Version]:
    brew_args = ['info', '--json', 'dbt']
    logger.debug(f"Running `brew` with arguments {brew_args}.")
    brew_result = subprocess.run(['brew', *brew_args], stdout=subprocess.PIPE)
    if brew_result.returncode != 0:
        raise dbtenv.DbtenvError("Failed to get dbt info from Homebrew.")
    formula_metadata = json.loads(brew_result.stdout)
    return [dbtenv.Version(re.sub(r'^dbt@', '', formula)) for formula in formula_metadata[0]['versioned_formulae']]
