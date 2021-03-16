import argparse
import http
import http.server
import json
import os
import os.path
import re
import subprocess
import threading
from typing import List, Optional, Union
import urllib.request

import dbtenv
import dbtenv.which


logger = dbtenv.LOGGER


def build_install_args_parser(subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
    description = """
        Install the specified dbt version from the Python Package Index or the specified package location using pip,
        or optionally using Homebrew on Mac or Linux.
    """
    parser = subparsers.add_parser(
        'install',
        parents=parent_parsers,
        description=description,
        help=description
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help="Install even if the dbt version appears to already be installed."
    )
    parser.add_argument(
        'dbt_version',
        type=dbtenv.Version,
        metavar='<dbt_version>',
        help="Exact version of dbt to install."
    )
    parser.add_argument(
        'package_location',
        nargs='?',
        metavar='<package_location>',
        help="""
            When installing using pip, the optional location of the dbt package to install, which can be a pip-compatible
            version control project URL, local project path, or archive URL/path.
            If not specified, dbt will be installed from the Python Package Index.
        """
    )
    parser.add_argument(
        '-e',
        '--editable',
        action='store_true',
        help="""
            When installing a dbt package from a version control project URL or local project path using pip, install it
            in "editable" mode.
        """
    )


def run_install_command(args: dbtenv.Args) -> None:
    installer = dbtenv.ENV.installer or dbtenv.ENV.default_installer
    if installer == dbtenv.Installer.PIP:
        venv_install(args.dbt_version, force=args.force, package_location=args.package_location, editable=args.editable)
    elif installer == dbtenv.Installer.HOMEBREW:
        homebrew_install(args.dbt_version, force=args.force)
    else:
        raise dbtenv.DbtenvError(f"Unknown installer `{installer}`.")


def install(dbt_version: dbtenv.Version) -> None:
    installer = dbtenv.ENV.installer or dbtenv.ENV.default_installer
    if installer == dbtenv.Installer.PIP:
        venv_install(dbt_version)
    elif installer == dbtenv.Installer.HOMEBREW:
        homebrew_install(dbt_version)
    else:
        raise dbtenv.DbtenvError(f"Unknown installer `{installer}`.")


def venv_install(dbt_version: dbtenv.Version, force: bool = False, package_location: Optional[str] = None, editable: bool = False) -> None:
    venv_dir = dbtenv.which.get_venv_dbt_directory(dbt_version)
    if os.path.isdir(venv_dir) and any(os.scandir(venv_dir)):
        if force:
            logger.info(f"`{venv_dir}` already exists but will be overwritten because --force was specified.")
        else:
            raise dbtenv.DbtenvError(f"`{venv_dir}` already exists.  Specify --force to overwrite it.")

    python = dbtenv.ENV.python
    _check_python_compatibility(python)

    logger.info(f"Creating virtual environment in `{venv_dir}` using `{python}`.")
    venv_result = subprocess.run([python, '-m' 'venv', '--clear', venv_dir])
    if venv_result.returncode != 0:
        raise dbtenv.DbtenvError(f"Failed to create virtual environment in `{venv_dir}`.")

    pip = _find_pip(venv_dir)
    pip_args = ['install', '--disable-pip-version-check']
    if package_location:
        package_source = f"`{package_location}`"
        if editable:
            pip_args.append('--editable')
        pip_args.append(package_location)
    else:
        package_source = "the Python Package Index"
        if dbtenv.ENV.simulate_release_date:
            dbt_release_date = _get_dbt_release_date(dbt_version)
            logger.info(f"Simulating release date {dbt_release_date} for dbt {dbt_version}.")
            class DateFilterPyPIRequestHandler(BaseDateFilterPyPIRequestHandler):
                date = dbt_release_date
            pip_filter_server = http.server.HTTPServer(('', 0), DateFilterPyPIRequestHandler)
            pip_filter_port = pip_filter_server.socket.getsockname()[1]
            threading.Thread(target=pip_filter_server.serve_forever, daemon=True).start()
            pip_args.extend(['--index-url', f'http://localhost:{pip_filter_port}/simple'])
        else:
            # agate 1.6.2 introduced a dependency on PyICU which causes installation problems, so exclude that.
            pip_args.append('agate>=1.6,<1.6.2')
        pip_args.append(f'dbt=={dbt_version.pypi_version}')
    logger.info(f"Installing dbt {dbt_version.pypi_version} from {package_source} into `{venv_dir}`.")

    logger.debug(f"Running `{pip}` with arguments {pip_args}.")
    pip_result = subprocess.run([pip, *pip_args])
    if pip_result.returncode != 0:
        raise dbtenv.DbtenvError(f"Failed to install dbt {dbt_version.pypi_version} from {package_source} into `{venv_dir}`.")

    logger.info(f"Successfully installed dbt {dbt_version.pypi_version} from {package_source} into `{venv_dir}`.")


def homebrew_install(dbt_version: dbtenv.Version, force: bool = False) -> None:
    already_installed = dbtenv.which.is_homebrew_dbt_installed(dbt_version)
    if already_installed:
        if force:
            logger.info(f"dbt {dbt_version.homebrew_version} is already installed with Homebrew but will be reinstalled because --force was specified.")
        else:
            raise dbtenv.DbtenvError(f"dbt {dbt_version.homebrew_version} is already installed with Homebrew.  Specify --force to reinstall it.")

    brew_args = []
    if already_installed and force:
        brew_args.append('reinstall')
    else:
        brew_args.append('install')
    brew_args.append(f'dbt@{dbt_version.homebrew_version}')
    logger.info(f"Installing dbt {dbt_version.homebrew_version} with Homebrew.")

    logger.debug(f"Running `brew` with arguments {brew_args}.")
    brew_result = subprocess.run(['brew', *brew_args])
    if brew_result.returncode != 0:
        raise dbtenv.DbtenvError(f"Failed to install dbt {dbt_version.homebrew_version} with Homebrew.")

    logger.info(f"Successfully installed dbt {dbt_version.homebrew_version} with Homebrew.")


def ensure_dbt_version_installed(dbt_version: dbtenv.Version) -> None:
    if not dbtenv.which.try_get_dbt(dbt_version):
        if dbtenv.ENV.auto_install:
            install(dbt_version)
        else:
            raise dbtenv.DbtenvError(f"No dbt {dbt_version} installation found and auto-install is not enabled.")


def get_pypi_package_metadata(package: str) -> str:
    package_json_url = f'https://pypi.org/pypi/{package}/json'
    logger.debug(f"Fetching {package} package metadata from {package_json_url}.")
    with urllib.request.urlopen(package_json_url) as package_json_response:
        return json.load(package_json_response)


def _check_python_compatibility(python: str) -> None:
    python_version_result = subprocess.run([python, '--version'], stdout=subprocess.PIPE, text=True)
    if python_version_result.returncode != 0:
        raise dbtenv.DbtenvError(f"Failed to run `{python}`.")
    python_version_output = python_version_result.stdout.strip()
    python_version_match = re.search(r'(\d+)\.(\d+)\.\d+\S*', python_version_output)
    if not python_version_match:
        raise dbtenv.DbtenvError(f"No Python version number found in \"{python_version_output}\".")
    python_version = python_version_match[0]
    python_major_version = int(python_version_match[1])
    python_minor_version = int(python_version_match[2])

    if (python_major_version, python_minor_version) >= (3, 9):
        raise dbtenv.DbtenvError(
            f"Python {python_version} is being used, but dbt currently isn't compatible with Python 3.9 or above."
        )

    logger.debug(f"Python {python_version} should be compatible with dbt.")


def _find_pip(venv_directory: str) -> str:
    pip_subpath = 'Scripts\\pip.exe' if dbtenv.ENV.os == 'Windows' else 'bin/pip'
    pip_path = os.path.join(venv_directory, pip_subpath)
    if os.path.isfile(pip_path):
        logger.debug(f"Found pip executable `{pip_path}`.")
        return pip_path

    raise dbtenv.DbtenvError(f"No pip executable found in `{venv_directory}`.")


def _get_dbt_release_date(dbt_version: dbtenv.Version) -> str:
    package_metadata = get_pypi_package_metadata('dbt')
    return package_metadata['releases'][dbt_version.pypi_version][0]['upload_time'][:10]


class BaseDateFilterPyPIRequestHandler(http.server.BaseHTTPRequestHandler):
    # self.date needs to be defined when this class is subclassed (we can't pass the date to use via a constructor
    # argument because the HTTPServer code instantiates request handlers in a very specific way).

    def do_GET(self) -> None:
        logger.debug(f"Handling pypi.org request:  {self.requestline}")
        package_match = re.search(r'^/simple/([^/]+)', self.path)

        passthrough_request_headers = {
            header: value
            for header, value in self.headers.items()
            if header in ('User-Agent', 'Accept', 'Cache-Control')
        }
        pypi_request = urllib.request.Request(f'https://pypi.org{self.path}', headers=passthrough_request_headers)
        with urllib.request.urlopen(pypi_request) as pypi_response:
            pypi_response_status  = pypi_response.status
            pypi_response_headers = pypi_response.headers
            pypi_response_body    = pypi_response.read()

        if (pypi_response_status != http.HTTPStatus.OK or not package_match):
            logger.debug(f"Passing through pypi.org {pypi_response_status} response for {self.path}.")
            self.send_response(pypi_response_status)
            for header, value in pypi_response_headers.items():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(pypi_response_body)
            return

        package = package_match[1]
        package_metadata = get_pypi_package_metadata(package)
        excluded_file_names = set(
            file['filename']
            for files in package_metadata['releases'].values()
            for file in files
            if file['upload_time'][:10] > self.date
        )
        excluded_file_link_count = 0
        def exclude_file_links(link_match: re.Match) -> str:
            nonlocal excluded_file_link_count
            if link_match[1].strip() in excluded_file_names:
                excluded_file_link_count += 1
                return ''
            else:
                return link_match[0]
        modified_response_body = re.sub(r'<a href=[^>]+>([^<]+)</a>', exclude_file_links, pypi_response_body.decode('utf-8')).encode('utf-8')
        logger.debug(f"Excluded {excluded_file_link_count} files for {package} after {self.date}.")

        self.send_response(pypi_response_status)
        for header, value in pypi_response_headers.items():
            if header != 'Content-Length':
                self.send_header(header, value)
        self.send_header('Content-Length', len(modified_response_body))
        self.end_headers()
        self.wfile.write(modified_response_body)

    def log_request(self, code: Union[int, str] = '-', size: Union[int, str] = '-') -> None:
        # We're already logging requests in do_GET(), so don't log them again here.
        pass
