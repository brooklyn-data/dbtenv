# Standard library
from datetime import date
import http
import http.server
import json
import os
import os.path
import re
import shutil
import subprocess
import threading
from typing import List, Optional, Union
import urllib.request

# Local
import dbtenv
from dbtenv import Dbt, DbtenvError, Environment, Version


logger = dbtenv.LOGGER

DBT_ADAPTER_TYPES = [
    'bigquery',
    'clickhouse',
    'databricks',
    'databricks',
    'dremio',
    'exasol',
    'firebolt',
    'firebolt',
    'materialize',
    'materialize',
    'oracle',
    'postgres',
    'presto',
    'redshift',
    'rockset',
    'rockset',
    'singlestore',
    'singlestore',
    'snowflake',
    'spark',
    'sqlserver',
    'synapse',
    'teradata',
    'teradata',
    'trino',
    'trino',
    'vertica',
]


def get_installed_pip_dbt_versions(env: Environment, adapter_type: Optional[str] = None) -> List[Version]:
    if not os.path.isdir(env.venvs_directory):
        return []
    versions = []
    for entry in os.scandir(env.venvs_directory):
        if entry.is_dir() and bool(re.search(r"^(dbt-.+)==(.+)$", entry.name)) and (not adapter_type or entry.name.startswith(f"dbt-{adapter_type}==")):
            versions.append(
                Version(pip_specifier=entry.name)
            )
    return versions


def get_pypi_package_metadata(package: str) -> str:
    package_json_url = f'https://pypi.org/pypi/{package}/json'
    logger.debug(f"Fetching {package} package metadata from {package_json_url}.")
    with urllib.request.urlopen(package_json_url) as package_json_response:
        return json.load(package_json_response)

def get_pypi_package_versions(adapter_type: str) -> List[Version]:
    package_metadata = get_pypi_package_metadata(f"dbt-{adapter_type}")
    possible_versions = ((Version(adapter_type=adapter_type, version=version), files) for version, files in package_metadata['releases'].items())
    return [version for version, files in possible_versions if any(not file['yanked'] for file in files)]

def get_pypi_all_dbt_package_versions() -> List[Version]:
    versions = []
    for adapter_type in DBT_ADAPTER_TYPES:
        versions += get_pypi_package_versions(adapter_type)
    return versions


class PipDbt(Dbt):
    """A specific version of dbt installed with pip in a Python virtual environment."""

    def __init__(self, env: Environment, version: Version) -> None:
        super().__init__(env, version)
        self.venv_directory = os.path.join(env.venvs_directory, version.pip_specifier)
        self._executable: Optional[str] = None

    def install(self, force: bool = False, package_location: Optional[str] = None, editable: bool = False) -> None:
        if self.is_installed():
            if force:
                logger.info(f"`{self.venv_directory}` already exists but will be overwritten.")
                self._executable = None
            else:
                raise DbtenvError(f"`{self.venv_directory}` already exists.")

        available_adapter_versions = get_pypi_package_versions(adapter_type=self.version.adapter_type)
        if self.version not in available_adapter_versions:
            logger.info(f"{self.version} is not available for installation from pypi. Try one of {[v.pypi_version for v in available_adapter_versions]}")
            return

        python = self.env.python
        self._check_python_compatibility(python)

        logger.info(f"Creating virtual environment in `{self.venv_directory}` using `{python}`.")
        venv_result = subprocess.run([python, '-m' 'venv', '--clear', self.venv_directory])
        if venv_result.returncode != 0:
            raise DbtenvError(f"Failed to create virtual environment in `{self.venv_directory}`.")

        try:
            pip = self._find_pip()
            # Upgrade pip to avoid problems with packages that might require newer pip features.
            subprocess.run([pip, 'install', '--upgrade', 'pip'])
            # Install wheel to avoid pip falling back to using legacy `setup.py` installs.
            subprocess.run([pip, 'install', '--disable-pip-version-check', 'wheel'])
            pip_args = ['install', '--disable-pip-version-check']
            if package_location:
                package_source = f"`{package_location}`"
                if editable:
                    pip_args.append('--editable')
                pip_args.append(package_location)
            else:
                package_source = "the Python Package Index"
                if self.env.simulate_release_date:
                    package_metadata = get_pypi_package_metadata('dbt')
                    release_date = date.fromisoformat(package_metadata['releases'][self.version.pypi_version][0]['upload_time'][:10])
                    logger.info(f"Simulating release date {release_date} for dbt {self.version}.")
                    class ReleaseDateFilterPyPIRequestHandler(BaseDateFilterPyPIRequestHandler):
                        date = release_date
                    pip_filter_server = http.server.HTTPServer(('', 0), ReleaseDateFilterPyPIRequestHandler)
                    pip_filter_port = pip_filter_server.socket.getsockname()[1]
                    threading.Thread(target=pip_filter_server.serve_forever, daemon=True).start()
                    pip_args.extend(['--index-url', f'http://localhost:{pip_filter_port}/simple'])
                elif self.version.pypi_version < '0.19.1':
                    # Versions prior to 0.19.1 just specified agate>=1.6, but agate 1.6.2 introduced a dependency on PyICU
                    # which causes installation problems, so exclude that like versions 0.19.1 and above do.
                    pip_args.append('agate>=1.6,<1.6.2')

                pip_args.append(self.version.pip_specifier)
            logger.info(f"Installing {self.version.pip_specifier} from {package_source} into `{self.venv_directory}`.")

            logger.debug(f"Running `{pip}` with arguments {pip_args}.")
            pip_result = subprocess.run([pip, *pip_args])
            if pip_result.returncode != 0:
                raise DbtenvError(f"Failed to install dbt {self.version.pypi_version} from {package_source} into `{self.venv_directory}`.")
        except Exception as e:
            shutil.rmtree(self.venv_directory)
            raise(e)

        logger.info(f"Successfully installed {self.version} from {package_source} into `{self.venv_directory}`.")

    def _check_python_compatibility(self, python: str) -> None:
        python_version_result = subprocess.run([python, '--version'], stdout=subprocess.PIPE)
        if python_version_result.returncode != 0:
            raise DbtenvError(f"Failed to run `{python}`.")
        python_version_output = python_version_result.stdout.decode('utf-8').strip()
        python_version_match = re.search(r'(?P<major_version>\d+)\.(?P<minor_version>\d+)\.\d+', python_version_output)
        if not python_version_match:
            raise DbtenvError(f"No Python version number found in \"{python_version_output}\".")
        python_version = python_version_match[0]
        python_major_version = int(python_version_match['major_version'])
        python_minor_version = int(python_version_match['minor_version'])

        if self.version.pypi_version < '0.20' and (python_major_version, python_minor_version) >= (3, 9):
            raise DbtenvError(
                f"Python {python_version} is being used, but dbt versions before 0.20.0 aren't compatible with Python 3.9 or above."
            )
        elif self.version.pypi_version < '0.15' and (python_major_version, python_minor_version) >= (3, 8):
            raise DbtenvError(
                f"Python {python_version} is being used, but dbt versions before 0.15 aren't compatible with Python 3.8 or above."
            )

        logger.debug(f"Python {python_version} should be compatible with dbt.")

    def _find_pip(self) -> str:
        pip_subpath = 'Scripts\\pip.exe' if self.env.os == 'Windows' else 'bin/pip'
        pip_path = os.path.join(self.venv_directory, pip_subpath)
        if os.path.isfile(pip_path):
            logger.debug(f"Found pip executable `{pip_path}`.")
            return pip_path
        else:
            raise DbtenvError(f"No pip executable found in `{self.venv_directory}`.")

    def get_executable(self) -> str:
        if self._executable is None:
            if not os.path.isdir(self.venv_directory):
                raise DbtenvError(f"No dbt {self.version.pypi_version} installation found in `{self.venv_directory}`.")

            dbt_subpath = 'Scripts\\dbt.exe' if self.env.os == 'Windows' else 'bin/dbt'
            dbt_path = os.path.join(self.venv_directory, dbt_subpath)
            if os.path.isfile(dbt_path):
                logger.debug(f"Found dbt executable `{dbt_path}`.")
                self._executable = dbt_path
            else:
                raise DbtenvError(f"No dbt executable found in `{self.venv_directory}`.")

        return self._executable

    def execute(self, args: List[str]) -> None:
        try:
            return super().execute(args)
        except FileNotFoundError:
            # FileNotFoundError can occur if the Python installation used to create the virtual environment no longer exists.
            # One common way that can happen is if a Homebrew-installed Python was used and subsequently upgraded.
            executable_dir = os.path.dirname(self._executable)
            with os.scandir(executable_dir) as executable_dir_scan:
                broken_python_symlinks = [
                    entry
                    for entry in executable_dir_scan
                    if entry.name.startswith('python')
                        and entry.is_symlink()
                        and os.path.sep in os.readlink(entry.path)  # Ignore local symlinks like `python` -> `python3`.
                        and not os.path.exists(entry.path)
                ]
            if broken_python_symlinks:
                broken_symlink = broken_python_symlinks[0]
                broken_symlink_target = os.readlink(broken_symlink.path)
                logger.error(
                    f"The virtual environment for dbt {self.version.pypi_version} is broken because the"
                    f" `{broken_symlink.path}` symlink points to `{broken_symlink_target}`, which no longer exists."
                )
                if dbtenv.string_is_true(input(f"Reinstall dbt {self.version.pypi_version} using `{self.env.python}`? ")):
                    self.install(force=True)
                    return super().execute(args)
            raise

    def uninstall(self, force: bool = False) -> None:
        if not self.is_installed():
            raise DbtenvError(f"No dbt {self.version.pypi_version} installation found in `{self.venv_directory}`.")

        if force or dbtenv.string_is_true(input(f"Uninstall `{self.venv_directory}`? ")):
            shutil.rmtree(self.venv_directory)
            self._executable = None
            logger.info(f"Successfully uninstalled dbt {self.version.pypi_version} from `{self.venv_directory}`.")


class BaseDateFilterPyPIRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler that proxies PEP 503-compliant requests to pypi.org and excludes files uploaded after self.date.

    self.date needs to be manually defined when this class is subclassed (we can't pass the date to use via a
    constructor argument because the HTTPServer code instantiates request handlers in a very specific way).
    """

    def do_GET(self) -> None:
        logger.debug(f"Handling pypi.org request:  {self.requestline}")
        package_match = re.search(r'^/simple/(?P<package>[^/]+)', self.path)

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

        package = package_match['package']
        package_metadata = get_pypi_package_metadata(package)
        excluded_file_names = set(
            file['filename']
            for files in package_metadata['releases'].values()
            for file in files
            if date.fromisoformat(file['upload_time'][:10]) > self.date
        )
        file_link_pattern = r'<a href=[^>]+>(?P<file_name>[^<]+)</a>'
        excluded_file_link_count = 0
        def exclude_file_links(link_match: re.Match) -> str:
            nonlocal excluded_file_link_count
            if link_match['file_name'].strip() in excluded_file_names:
                excluded_file_link_count += 1
                return ''
            else:
                return link_match[0]
        modified_response_body = re.sub(file_link_pattern, exclude_file_links, pypi_response_body.decode('utf-8')).encode('utf-8')
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
