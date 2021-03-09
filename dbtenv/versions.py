import argparse
import distutils.version
import json
import os
from typing import List
import urllib.request

import dbtenv
import dbtenv.version
import dbtenv.which


logger = dbtenv.LOGGER


def build_versions_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    description = "Show the dbt versions that are available from the Python Package Index or that are installed."
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


def run_versions_command(parsed_args: argparse.Namespace) -> None:
    installed_versions = set(get_installed_dbt_versions())
    active_version, active_version_source = dbtenv.version.get_version(os.getcwd())

    distinct_versions = installed_versions.copy()
    if not parsed_args.installed:
        distinct_versions.update(get_dbt_package_versions())

    versions = list(distinct_versions)
    versions.sort(key=distutils.version.LooseVersion)

    if versions:
        logger.info("+ = installed, * = active")
        for version in versions:
            if version == active_version:
                print(f"* {version}  (set by {active_version_source})")
            elif version in installed_versions:
                print(f"+ {version}")
            else:
                print(f"  {version}")
    else:
        logger.info(f"No dbt installations found in `{dbtenv.get_versions_directory()}`.")


def get_installed_dbt_versions() -> List[str]:
    return [entry.name for entry in os.scandir(dbtenv.get_versions_directory()) if dbtenv.which.try_get_dbt(entry.name)]


def get_dbt_package_versions() -> List[str]:
    logger.debug(f"Fetching dbt package data from {dbtenv.DBT_PACKAGE_JSON_URL}.")
    with urllib.request.urlopen(dbtenv.DBT_PACKAGE_JSON_URL) as package_response:
        package_data = json.load(package_response)
    return [version for version, files in package_data['releases'].items() if any(not file['yanked'] for file in files)]
