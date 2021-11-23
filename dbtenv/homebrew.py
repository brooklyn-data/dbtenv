# Standard library
import glob
import json
import os
import os.path
import re
import subprocess
from typing import List, Optional

# Local
import dbtenv
from dbtenv import Dbt, DbtenvError, Environment, Version


logger = dbtenv.LOGGER


def get_dbt_formula_version(formula: str) -> Version:
    return Version(re.sub(r'^dbt@', '', formula))


def get_dbt_version_formula(version: Version) -> str:
    return f'dbt@{version.homebrew_version}'


def get_dbt_version_keg_directory(env: Environment, version: Version) -> str:
    return os.path.join(env.homebrew_prefix_directory, 'opt', get_dbt_version_formula(version))


def ensure_homebrew_dbt_tap() -> None:
    # While it would be simplest to just always run `brew tap dbt-labs/dbt`, we need to first check for
    # an existing dbt tap because the "dbt-labs" GitHub organization used to be named "fishtown-analytics"
    # so people could have a "fishtown-analytics/dbt" tap, and having multiple dbt taps causes errors.
    tap_list_result = subprocess.run(['brew', 'tap'], stdout=subprocess.PIPE, text=True)
    if not re.search(r'\b(fishtown-analytics|dbt-labs)/dbt\b', tap_list_result.stdout):
        logger.info('Adding the dbt Homebrew tap.')
        tap_dbt_result = subprocess.run(['brew', 'tap', 'dbt-labs/dbt'])
        if tap_dbt_result.returncode != 0:
            raise DbtenvError("Failed to add the dbt Homebrew tap.")


def get_homebrew_dbt_versions() -> List[Version]:
    ensure_homebrew_dbt_tap()
    brew_args = ['info', '--json', 'dbt']
    logger.debug(f"Running `brew` with arguments {brew_args}.")
    brew_result = subprocess.run(['brew', *brew_args], stdout=subprocess.PIPE)
    if brew_result.returncode != 0:
        raise DbtenvError("Failed to get dbt info from Homebrew.")
    formula_metadata = json.loads(brew_result.stdout)
    return [get_dbt_formula_version(formula) for formula in formula_metadata[0]['versioned_formulae']]


def get_installed_homebrew_dbt_versions(env: Environment) -> List[Version]:
    versioned_keg_dir_pattern = get_dbt_version_keg_directory(env, Version('*'))
    versioned_formulae = (os.path.basename(keg_dir) for keg_dir in glob.glob(versioned_keg_dir_pattern))
    possible_versions = (get_dbt_formula_version(formula) for formula in versioned_formulae)
    return [version for version in possible_versions if HomebrewDbt(env, version).is_installed()]


class HomebrewDbt(Dbt):
    """A specific version of dbt installed with Homebrew."""

    def __init__(self, env: Environment, version: Version) -> None:
        super().__init__(env, version)
        self.keg_directory = get_dbt_version_keg_directory(env, version)
        self._executable: Optional[str] = None

    def install(self, force: bool = False) -> None:
        if self.is_installed():
            if force:
                logger.info(f"dbt {self.version.homebrew_version} is already installed with Homebrew but will be reinstalled.")
                self.uninstall(force=True)
            else:
                raise DbtenvError(f"dbt {self.version.homebrew_version} is already installed with Homebrew.")
        else:
            ensure_homebrew_dbt_tap()

        logger.info(f"Installing dbt {self.version.homebrew_version} with Homebrew.")
        brew_args = ['install', get_dbt_version_formula(self.version)]
        logger.debug(f"Running `brew` with arguments {brew_args}.")
        subprocess.run(['brew', *brew_args])
        # We can't rely on the Homebrew process return code to check for success/failure because a non-zero return code
        # might just indicate some extraneous problem, like a failure symlinking dbt into the bin directory.
        if self.is_installed():
            logger.info(f"Successfully installed dbt {self.version.homebrew_version} with Homebrew.")
        else:
            raise DbtenvError(f"Failed to install dbt {self.version.homebrew_version} with Homebrew.")

    def get_executable(self) -> str:
        if self._executable is None:
            if not os.path.isdir(self.keg_directory):
                raise DbtenvError(f"No dbt {self.version.homebrew_version} installation found in `{self.keg_directory}`.")

            dbt_path = os.path.join(self.keg_directory, 'bin/dbt')
            if os.path.isfile(dbt_path):
                logger.debug(f"Found dbt executable `{dbt_path}`.")
                self._executable = dbt_path
            else:
                raise DbtenvError(f"No dbt executable found in `{self.keg_directory}`.")

        return self._executable

    def uninstall(self, force: bool = False) -> None:
        if not self.is_installed():
            raise DbtenvError(f"No dbt {self.version.homebrew_version} installation found in `{self.keg_directory}`.")

        if force or dbtenv.string_is_true(input(f"Uninstall dbt {self.version.homebrew_version} from Homebrew? ")):
            brew_args = ['uninstall']
            if force:
                brew_args.append('--force')
            brew_args.append(get_dbt_version_formula(self.version))
            logger.debug(f"Running `brew` with arguments {brew_args}.")
            brew_result = subprocess.run(['brew', *brew_args])
            if brew_result.returncode != 0:
                raise DbtenvError(f"Failed to uninstall dbt {self.version.homebrew_version} from Homebrew.")
            self._executable = None
            logger.info(f"Successfully uninstalled dbt {self.version.homebrew_version} from Homebrew.")
