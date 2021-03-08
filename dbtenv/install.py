import argparse
import os
import os.path
import re
import subprocess

import dbtenv


logger = dbtenv.LOGGER


def build_install_args_parser(subparsers: argparse._SubParsersAction) -> None:
    install_parser = subparsers.add_parser(
        'install',
        help="Install the specified dbt version from the Python Package Index or the specified package location."
    )
    install_parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help="Install even if the dbt version appears to already be installed."
    )
    install_parser.add_argument('dbt_version', help="Exact version of dbt to install.")
    install_parser.add_argument(
        'package_location',
        nargs='?',
        help="""
            Location of the dbt package to install, which can be a pip-compatible version control project URL, local
            project path, or archive URL/path.
            If not specified, dbt will be installed from the Python Package Index.
        """
    )
    install_parser.add_argument(
        '-e',
        '--editable',
        action='store_true',
        help="Install a dbt package from a version control project URL or local project path in \"editable\" mode."
    )


def install(parsed_args: argparse.Namespace) -> None:
    dbt_version = parsed_args.dbt_version
    dbt_version_dir = dbtenv.get_version_directory(dbt_version)
    if os.path.isdir(dbt_version_dir) and any(os.scandir(dbt_version_dir)):
        if parsed_args.force:
            logger.info(f"`{dbt_version_dir}` already exists but will be overwritten because --force was specified.")
        else:
            raise dbtenv.DbtenvRuntimeError(f"`{dbt_version_dir}` already exists.  Specify --force to overwrite it.")

    python = dbtenv.get_python()
    _check_python_compatibility(python)

    logger.debug(f"Creating virtual environment in `{dbt_version_dir}` using `{python}`.")
    venv_result = subprocess.run([python, '-m' 'venv', '--clear', dbt_version_dir])
    if venv_result.returncode != 0:
        raise dbtenv.DbtenvRuntimeError(f"Failed to create virtual environment in `{dbt_version_dir}`.")

    pip = _find_pip(dbt_version_dir)
    pip_args = ['install', '--pre', '--no-cache-dir', '--disable-pip-version-check']
    package_location = parsed_args.package_location
    package_source = f"`{package_location}`" if package_location else "the Python Package Index"
    if package_location:
        if parsed_args.editable:
            pip_args.append('--editable')
        pip_args.append(package_location)
    else:
        pip_args.append(f'dbt=={dbt_version}')
    logger.info(f"Installing dbt {dbt_version} from {package_source} in `{dbt_version_dir}`.")
    logger.debug(f"Running pip with arguments {pip_args}.")
    pip_result = subprocess.run([pip, *pip_args])
    if pip_result.returncode != 0:
        raise dbtenv.DbtenvRuntimeError(
            f"Failed to install dbt {dbt_version} from {package_source} in `{dbt_version_dir}`."
        )

    logger.info(f"Successfully installed dbt {dbt_version} from {package_source} in `{dbt_version_dir}`.")


def _check_python_compatibility(python: str) -> None:
    python_version_result = subprocess.run([python, '--version'], stdout=subprocess.PIPE, text=True)
    if python_version_result.returncode != 0:
        raise dbtenv.DbtenvRuntimeError(f"Failed to run `{python}`.")
    python_version_output = python_version_result.stdout.strip()
    python_version_match = re.search(r'(\d+)\.(\d+)\.\d+\S*', python_version_output)
    if not python_version_match:
        raise dbtenv.DbtenvRuntimeError(f"No Python version number found in \"{python_version_output}\".")
    python_version = python_version_match[0]
    python_major_version = int(python_version_match[1])
    python_minor_version = int(python_version_match[2])

    if python_major_version == 3 and python_minor_version >= 9:
        raise dbtenv.DbtenvRuntimeError(
            f"Python {python_version} is being used, but dbt currently isn't compatible with Python 3.9 or above."
        )

    logger.debug(f"Python {python_version} should be compatible with dbt.")


def _find_pip(venv_path: str) -> str:
    for possible_pip_subpath_parts in [['bin', 'pip'], ['Scripts', 'pip.exe']]:
        pip_path = os.path.join(venv_path, *possible_pip_subpath_parts)
        if os.path.isfile(pip_path):
            logger.debug(f"Found pip executable `{pip_path}`.")
            return pip_path

    raise dbtenv.DbtenvRuntimeError(f"No pip executable found in `{venv_path}`.")
