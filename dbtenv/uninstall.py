import argparse
import os
import os.path
import shutil
import subprocess
from typing import List

import dbtenv
import dbtenv.which


logger = dbtenv.LOGGER


def build_uninstall_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    description = "Uninstall the specified dbt version."
    parser = subparsers.add_parser(
        'uninstall',
        parents=parent_parsers,
        description=description,
        help=description
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help="Uninstall without prompting for confirmation."
    )
    parser.add_argument(
        'dbt_version',
        type=dbtenv.Version,
        metavar='<dbt_version>',
        help="Exact version of dbt to uninstall."
    )


def run_uninstall_command(args: dbtenv.Args) -> None:
    uninstall_all           = not dbtenv.ENV.installer
    only_uninstall_venv     = dbtenv.ENV.installer == dbtenv.Installer.PIP
    only_uninstall_homebrew = dbtenv.ENV.installer == dbtenv.Installer.HOMEBREW
    uninstall_venv          = uninstall_all or only_uninstall_venv
    uninstall_homebrew      = (uninstall_all or only_uninstall_homebrew) and dbtenv.ENV.homebrew_installed

    attempted_uninstalls = 0

    if uninstall_venv and dbtenv.which.is_venv_dbt_installed(args.dbt_version):
        venv_uninstall(args.dbt_version, force=args.force)
        attempted_uninstalls += 1

    if uninstall_homebrew and dbtenv.which.is_homebrew_dbt_installed(args.dbt_version):
        homebrew_uninstall(args.dbt_version, force=args.force)
        attempted_uninstalls += 1

    if attempted_uninstalls == 0:
        raise dbtenv.DbtenvError(f"No dbt {args.dbt_version} installation found.")


def venv_uninstall(dbt_version: dbtenv.Version, force: bool = False) -> None:
    venv_dir = dbtenv.which.get_venv_dbt_directory(dbt_version)
    if not os.path.isdir(venv_dir):
        raise dbtenv.DbtenvError(f"No dbt {dbt_version.pypi_version} installation found in `{venv_dir}`.")

    if force or dbtenv.string_is_true(input(f"Uninstall dbt {dbt_version.pypi_version} from `{venv_dir}`? ")):
        shutil.rmtree(venv_dir)
        logger.info(f"Successfully uninstalled dbt {dbt_version.pypi_version} from `{venv_dir}`.")


def homebrew_uninstall(dbt_version: dbtenv.Version, force: bool = False) -> None:
    keg_dir = dbtenv.which.get_homebrew_dbt_directory(dbt_version)
    if not os.path.isdir(keg_dir):
        raise dbtenv.DbtenvError(f"No dbt {dbt_version.homebrew_version} installation found in `{keg_dir}`.")

    if force or dbtenv.string_is_true(input(f"Uninstall dbt {dbt_version} from Homebrew? ")):
        brew_args = ['uninstall', f'dbt@{dbt_version.homebrew_version}']
        logger.debug(f"Running `brew` with arguments {brew_args}.")
        brew_result = subprocess.run(['brew', *brew_args])
        if brew_result.returncode != 0:
            raise dbtenv.DbtenvError(f"Failed to uninstall dbt {dbt_version.homebrew_version} from Homebrew.")

        logger.info(f"Successfully uninstalled dbt {dbt_version.homebrew_version} from Homebrew.")
