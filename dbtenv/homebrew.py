import glob
import json
import os
import os.path
import re
import subprocess
from typing import List, Optional

import dbtenv


logger = dbtenv.LOGGER


def get_dbt_formula_version(formula: str) -> dbtenv.Version:
    return dbtenv.Version(re.sub(r'^dbt@', '', formula))


def get_dbt_version_formula(version: dbtenv.Version) -> str:
    return f'dbt@{version.homebrew_version}'


def get_dbt_version_keg_directory(env: dbtenv.Environment, version: dbtenv.Version) -> str:
    return os.path.join(env.homebrew_prefix_directory, 'opt', get_dbt_version_formula(version))


def get_homebrew_dbt_versions() -> List[dbtenv.Version]:
    brew_args = ['info', '--json', 'dbt']
    logger.debug(f"Running `brew` with arguments {brew_args}.")
    brew_result = subprocess.run(['brew', *brew_args], stdout=subprocess.PIPE)
    if brew_result.returncode != 0:
        raise dbtenv.DbtenvError("Failed to get dbt info from Homebrew.")
    formula_metadata = json.loads(brew_result.stdout)
    return [get_dbt_formula_version(formula) for formula in formula_metadata[0]['versioned_formulae']]


def get_installed_homebrew_dbt_versions(env: dbtenv.Environment) -> List[dbtenv.Version]:
    versioned_keg_dir_pattern = get_dbt_version_keg_directory(env, dbtenv.Version('*'))
    versioned_formulae = (os.path.basename(keg_dir) for keg_dir in glob.glob(versioned_keg_dir_pattern))
    possible_versions = (get_dbt_formula_version(formula) for formula in versioned_formulae)
    return [version for version in possible_versions if HomebrewDbt(env, version).is_installed()]


class HomebrewDbt(dbtenv.Dbt):
    """A specific version of dbt installed with Homebrew."""

    def __init__(self, env: dbtenv.Environment, version: dbtenv.Version) -> None:
        super().__init__(env, version)
        self.keg_directory = get_dbt_version_keg_directory(env, version)
        self._executable: Optional[str] = None

    def install(self, force: bool = False) -> None:
        if self.is_installed():
            if force:
                logger.info(f"dbt {self.version.homebrew_version} is already installed with Homebrew but will be reinstalled.")
                self.uninstall(force=True)
            else:
                raise dbtenv.DbtenvError(f"dbt {self.version.homebrew_version} is already installed with Homebrew.")

        logger.info(f"Installing dbt {self.version.homebrew_version} with Homebrew.")
        brew_args = ['install', get_dbt_version_formula(self.version)]
        logger.debug(f"Running `brew` with arguments {brew_args}.")
        brew_result = subprocess.run(['brew', *brew_args])
        if brew_result.returncode != 0:
            raise dbtenv.DbtenvError(f"Failed to install dbt {self.version.homebrew_version} with Homebrew.")

        logger.info(f"Successfully installed dbt {self.version.homebrew_version} with Homebrew.")

    def get_executable(self) -> str:
        if self._executable is None:
            if not os.path.isdir(self.keg_directory):
                raise dbtenv.DbtenvError(f"No dbt {self.version.homebrew_version} installation found in `{self.keg_directory}`.")

            dbt_path = os.path.join(self.keg_directory, 'bin/dbt')
            if os.path.isfile(dbt_path):
                logger.debug(f"Found dbt executable `{dbt_path}`.")
                self._executable = dbt_path
            else:
                raise dbtenv.DbtenvError(f"No dbt executable found in `{self.keg_directory}`.")

        return self._executable

    def uninstall(self, force: bool = False) -> None:
        if not self.is_installed():
            raise dbtenv.DbtenvError(f"No dbt {self.version.homebrew_version} installation found in `{self.keg_directory}`.")

        if force or dbtenv.string_is_true(input(f"Uninstall dbt {self.version.homebrew_version} from Homebrew? ")):
            brew_args = ['uninstall']
            if force:
                brew_args.append('--force')
            brew_args.append(get_dbt_version_formula(self.version))
            logger.debug(f"Running `brew` with arguments {brew_args}.")
            brew_result = subprocess.run(['brew', *brew_args])
            if brew_result.returncode != 0:
                raise dbtenv.DbtenvError(f"Failed to uninstall dbt {self.version.homebrew_version} from Homebrew.")
            self._executable = None
            logger.info(f"Successfully uninstalled dbt {self.version.homebrew_version} from Homebrew.")
