import argparse
import glob
import os
from typing import List, Optional

import dbtenv
import dbtenv.version


logger = dbtenv.LOGGER


def build_which_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        'which',
        parents=parent_parsers,
        description=f"""
            Show the full path to the executable of the specified dbt version or the dbt version automatically detected
            from the environment based on the global `{dbtenv.GLOBAL_VERSION_FILE}` file, local
            `{dbtenv.LOCAL_VERSION_FILE}` files, or {dbtenv.DBT_VERSION_VAR} environment variable.
        """,
        help="""
            Show the full path to the executable of the specified dbt version or the dbt version automatically detected
            from the environment.
        """
    )
    parser.add_argument(
        'dbt_version',
        nargs='?',
        type=dbtenv.Version,
        metavar='<dbt_version>',
        help="""
            Exact version of dbt to show.
            If not specified, the dbt version will be automatically detected from the environment.
        """
    )


def run_which_command(args: dbtenv.Args) -> None:
    if args.dbt_version:
        dbt_version = args.dbt_version
    else:
        dbt_version, dbt_version_source = dbtenv.version.get_version(os.getcwd())
        if dbt_version:
            logger.info(f"Using dbt {dbt_version} (set by {dbt_version_source}).")
        else:
            logger.info("No dbt version has been set globally, for the local directory, or for the current shell.")

    if dbt_version:
        print(get_dbt(dbt_version))


def get_venv_dbt_directory(dbt_version: dbtenv.Version) -> str:
    return os.path.join(dbtenv.ENV.venvs_directory, dbt_version.pypi_version)


def is_venv_dbt_installed(dbt_version: dbtenv.Version) -> bool:
    return os.path.isdir(get_venv_dbt_directory(dbt_version))


def get_venv_dbt(dbt_version: dbtenv.Version) -> str:
    venv_dir = get_venv_dbt_directory(dbt_version)
    if not os.path.isdir(venv_dir):
        raise dbtenv.DbtenvError(f"No dbt {dbt_version} installation found in `{venv_dir}`.")

    for possible_dbt_subpath_parts in [['bin', 'dbt'], ['Scripts', 'dbt.exe']]:
        dbt_path = os.path.join(venv_dir, *possible_dbt_subpath_parts)
        if os.path.isfile(dbt_path):
            logger.debug(f"Found dbt executable `{dbt_path}`.")
            return dbt_path

    raise dbtenv.DbtenvError(f"No dbt executable found in `{venv_dir}`.")


def try_get_venv_dbt(dbt_version: dbtenv.Version) -> Optional[str]:
    try:
        return get_venv_dbt(dbt_version)
    except:
        return None


def get_homebrew_dbt_directory(dbt_version: dbtenv.Version) -> str:
    return os.path.join(dbtenv.ENV.homebrew_cellar_directory, f'dbt@{dbt_version.homebrew_version}')


def is_homebrew_dbt_installed(dbt_version: dbtenv.Version) -> bool:
    return os.path.isdir(get_homebrew_dbt_directory(dbt_version))


def get_homebrew_dbt(dbt_version: dbtenv.Version) -> str:
    keg_dir = get_homebrew_dbt_directory(dbt_version)
    if not os.path.isdir(keg_dir):
        raise dbtenv.DbtenvError(f"No dbt {dbt_version.homebrew_version} installation found in `{keg_dir}`.")

    # We can't be sure what the installation subdirectory within the keg directory will be.
    dbt_paths = glob.glob(os.path.join(keg_dir, '*', 'bin', 'dbt'))
    if dbt_paths:
        logger.debug(f"Found dbt executable `{dbt_paths[0]}`.")
        return dbt_paths[0]

    raise dbtenv.DbtenvError(f"No dbt executable found in `{keg_dir}`.")


def try_get_homebrew_dbt(dbt_version: dbtenv.Version) -> Optional[str]:
    try:
        return get_homebrew_dbt(dbt_version)
    except:
        return None


def get_dbt(dbt_version: dbtenv.Version) -> str:
    primary_installer = dbtenv.ENV.installer or dbtenv.ENV.default_installer
    use_any_installer = not dbtenv.ENV.installer
    only_use_venv     = dbtenv.ENV.installer == dbtenv.Installer.PIP
    only_use_homebrew = dbtenv.ENV.installer == dbtenv.Installer.HOMEBREW
    use_venv          = use_any_installer or only_use_venv
    use_homebrew      = (use_any_installer or only_use_homebrew) and dbtenv.ENV.homebrew_installed
    prefer_venv       = primary_installer == dbtenv.Installer.PIP
    prefer_homebrew   = primary_installer == dbtenv.Installer.HOMEBREW

    error = dbtenv.DbtenvError(f"No dbt {dbt_version} executable found.")

    venv_dbt = None
    if use_venv:
        try:
            venv_dbt = get_venv_dbt(dbt_version)
            if prefer_venv:
                return venv_dbt
        except dbtenv.DbtenvError as venv_error:
            error = venv_error
            if only_use_venv:
                raise

    if use_homebrew:
        try:
            return get_homebrew_dbt(dbt_version)
        except dbtenv.DbtenvError:
            if only_use_homebrew or (prefer_homebrew and not venv_dbt):
                raise

    if venv_dbt:
        return venv_dbt

    raise error


def try_get_dbt(dbt_version: dbtenv.Version) -> Optional[str]:
    try:
        return get_dbt(dbt_version)
    except:
        return None
