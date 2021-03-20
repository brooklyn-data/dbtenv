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


def get_homebrew_dbt_versions() -> List[dbtenv.Version]:
    brew_args = ['info', '--json', 'dbt']
    logger.debug(f"Running `brew` with arguments {brew_args}.")
    brew_result = subprocess.run(['brew', *brew_args], stdout=subprocess.PIPE)
    if brew_result.returncode != 0:
        raise dbtenv.DbtenvError("Failed to get dbt info from Homebrew.")
    formula_metadata = json.loads(brew_result.stdout)
    return [get_dbt_formula_version(formula) for formula in formula_metadata[0]['versioned_formulae']]


def get_installed_homebrew_dbt_versions(env: dbtenv.Environment) -> List[dbtenv.Version]:
    versioned_keg_dir_pattern = os.path.join(env.homebrew_cellar_directory, 'dbt@*') + os.path.sep
    versioned_formulae = (os.path.basename(os.path.dirname(keg_dir)) for keg_dir in glob.glob(versioned_keg_dir_pattern))
    possible_versions = (get_dbt_formula_version(formula) for formula in versioned_formulae)
    return [version for version in possible_versions if HomebrewDbt(env, version).is_installed()]


class HomebrewDbt(dbtenv.Dbt):
    """A specific version of dbt installed with Homebrew."""

    def __init__(self, env: dbtenv.Environment, version: dbtenv.Version) -> None:
        super().__init__(env, version)
        self.keg_directory = os.path.join(env.homebrew_cellar_directory, f'dbt@{version.homebrew_version}')
        self._executable: Optional[str] = None

    def install(self, force: bool = False) -> None:
        already_installed = self.is_installed()
        if already_installed:
            if force:
                logger.info(f"dbt {self.version.homebrew_version} is already installed with Homebrew but will be reinstalled.")
                self._executable = None
            else:
                raise dbtenv.DbtenvError(f"dbt {self.version.homebrew_version} is already installed with Homebrew.")

        brew_args = []
        if already_installed and force:
            brew_args.append('reinstall')
        else:
            brew_args.append('install')
        brew_args.append(f'dbt@{self.version.homebrew_version}')
        logger.info(f"Installing dbt {self.version.homebrew_version} with Homebrew.")

        logger.debug(f"Running `brew` with arguments {brew_args}.")
        brew_result = subprocess.run(['brew', *brew_args])
        if brew_result.returncode != 0:
            raise dbtenv.DbtenvError(f"Failed to install dbt {self.version.homebrew_version} with Homebrew.")

        logger.info(f"Successfully installed dbt {self.version.homebrew_version} with Homebrew.")

    def get_executable(self) -> str:
        if self._executable is None:
            if not os.path.isdir(self.keg_directory):
                raise dbtenv.DbtenvError(f"No dbt {self.version.homebrew_version} installation found in `{self.keg_directory}`.")

            # We can't be sure what the installation subdirectory within the keg directory will be.
            dbt_paths = glob.glob(os.path.join(self.keg_directory, '*', 'bin', 'dbt'))
            if dbt_paths:
                logger.debug(f"Found dbt executable `{dbt_paths[0]}`.")
                self._executable = dbt_paths[0]
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
            brew_args.append(f'dbt@{self.version.homebrew_version}')
            logger.debug(f"Running `brew` with arguments {brew_args}.")
            brew_result = subprocess.run(['brew', *brew_args])
            if brew_result.returncode != 0:
                raise dbtenv.DbtenvError(f"Failed to uninstall dbt {self.version.homebrew_version} from Homebrew.")
            self._executable = None
            logger.info(f"Successfully uninstalled dbt {self.version.homebrew_version} from Homebrew.")
