import http
import http.server
import os
import os.path
import re
import shutil
import subprocess
import threading
from typing import List, Optional

import dbtenv
import dbtenv.pypi


logger = dbtenv.LOGGER


def get_installed_venv_dbt_versions(env: dbtenv.Environment) -> List[dbtenv.Version]:
    possible_versions = (dbtenv.Version(entry.name) for entry in os.scandir(env.venvs_directory) if os.path.isdir(entry))
    return [version for version in possible_versions if VenvDbt(env, version).is_installed()]


class VenvDbt(dbtenv.Dbt):
    """A specific version of dbt installed in a Python virtual environment."""

    def __init__(self, env: dbtenv.Environment, version: dbtenv.Version) -> None:
        super().__init__(env, version)
        self.venv_directory = os.path.join(env.venvs_directory, version.pypi_version)
        self._executable: Optional[str] = None

    def install(self, force: bool = False, package_location: Optional[str] = None, editable: bool = False) -> None:
        if self.is_installed():
            if force:
                logger.info(f"`{self.venv_directory}` already exists but will be overwritten.")
                self._executable = None
            else:
                raise dbtenv.DbtenvError(f"`{self.venv_directory}` already exists.")

        python = self.env.python
        self._check_python_compatibility(python)

        logger.info(f"Creating virtual environment in `{self.venv_directory}` using `{python}`.")
        venv_result = subprocess.run([python, '-m' 'venv', '--clear', self.venv_directory])
        if venv_result.returncode != 0:
            raise dbtenv.DbtenvError(f"Failed to create virtual environment in `{self.venv_directory}`.")

        pip = self._find_pip()
        pip_args = ['install', '--disable-pip-version-check']
        if package_location:
            package_source = f"`{package_location}`"
            if editable:
                pip_args.append('--editable')
            pip_args.append(package_location)
        else:
            package_source = "the Python Package Index"
            if self.env.simulate_release_date:
                package_metadata = dbtenv.pypi.get_pypi_package_metadata('dbt')
                release_date = package_metadata['releases'][self.version.pypi_version][0]['upload_time'][:10]
                logger.info(f"Simulating release date {release_date} for dbt {self.version}.")
                class ReleaseDateFilterPyPIRequestHandler(dbtenv.pypi.BaseDateFilterPyPIRequestHandler):
                    date = release_date
                pip_filter_server = http.server.HTTPServer(('', 0), ReleaseDateFilterPyPIRequestHandler)
                pip_filter_port = pip_filter_server.socket.getsockname()[1]
                threading.Thread(target=pip_filter_server.serve_forever, daemon=True).start()
                pip_args.extend(['--index-url', f'http://localhost:{pip_filter_port}/simple'])
            else:
                # agate 1.6.2 introduced a dependency on PyICU which causes installation problems, so exclude that.
                pip_args.append('agate>=1.6,<1.6.2')
            pip_args.append(f'dbt=={self.version.pypi_version}')
        logger.info(f"Installing dbt {self.version.pypi_version} from {package_source} into `{self.venv_directory}`.")

        logger.debug(f"Running `{pip}` with arguments {pip_args}.")
        pip_result = subprocess.run([pip, *pip_args])
        if pip_result.returncode != 0:
            raise dbtenv.DbtenvError(f"Failed to install dbt {self.version.pypi_version} from {package_source} into `{self.venv_directory}`.")

        logger.info(f"Successfully installed dbt {self.version.pypi_version} from {package_source} into `{self.venv_directory}`.")

    def _check_python_compatibility(self, python: str) -> None:
        python_version_result = subprocess.run([python, '--version'], stdout=subprocess.PIPE, text=True)
        if python_version_result.returncode != 0:
            raise dbtenv.DbtenvError(f"Failed to run `{python}`.")
        python_version_output = python_version_result.stdout.strip()
        python_version_match = re.search(r'(\d+)\.(\d+)\.\d+', python_version_output)
        if not python_version_match:
            raise dbtenv.DbtenvError(f"No Python version number found in \"{python_version_output}\".")
        python_version = python_version_match[0]
        python_major_version = int(python_version_match[1])
        python_minor_version = int(python_version_match[2])

        if (python_major_version, python_minor_version) >= (3, 9):
            raise dbtenv.DbtenvError(
                f"Python {python_version} is being used, but dbt currently isn't compatible with Python 3.9 or above."
            )
        elif self.version < dbtenv.Version('0.15') and (python_major_version, python_minor_version) >= (3, 8):
            raise dbtenv.DbtenvError(
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
            raise dbtenv.DbtenvError(f"No pip executable found in `{self.venv_directory}`.")

    def get_executable(self) -> str:
        if self._executable is None:
            if not os.path.isdir(self.venv_directory):
                raise dbtenv.DbtenvError(f"No dbt {self.version.pypi_version} installation found in `{self.venv_directory}`.")

            dbt_subpath = 'Scripts\\dbt.exe' if self.env.os == 'Windows' else 'bin/dbt'
            dbt_path = os.path.join(self.venv_directory, dbt_subpath)
            if os.path.isfile(dbt_path):
                logger.debug(f"Found dbt executable `{dbt_path}`.")
                self._executable = dbt_path
            else:
                raise dbtenv.DbtenvError(f"No dbt executable found in `{self.venv_directory}`.")

        return self._executable

    def uninstall(self, force: bool = False) -> None:
        if not self.is_installed():
            raise dbtenv.DbtenvError(f"No dbt {self.version.pypi_version} installation found in `{self.venv_directory}`.")

        if force or dbtenv.string_is_true(input(f"Uninstall dbt {self.version.pypi_version} from `{self.venv_directory}`? ")):
            shutil.rmtree(self.venv_directory)
            self._executable = None
            logger.info(f"Successfully uninstalled dbt {self.version.pypi_version} from `{self.venv_directory}`.")
