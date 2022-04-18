# dbtenv Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/brooklyn-data/dbtenv/compare/v2.1.0...HEAD)

### Added

### Changed

### Fixed

## [2.1.0](https://github.com/brooklyn-data/dbtenv/compare/v2.0.0...v2.1.0)

### Added
- Added compatibility with `dbtenv-dbt-alias` package which installs `dbt` as a direct entrypoint to dbtenv. This removes the need to configure an alias from dbt to dbtenv execute. Running `pip install dbtenv[dbt-alias]` installs both dbtenv and the alias.
- Improved logging for cases where dbtenv cannot determine the needed adapter type.
### Changed

### Fixed
- Fixed a bug encountered when using local version files.

## [2.0.0](https://github.com/brooklyn-data/dbtenv/compare/v2.0.0a2...v2.0.0)

### Added
- dbtenv now operates at the adapter-version level, introduced by dbt in version 1.0.0. dbtenv can automatically detect the needed adapter version from `profiles.yml`, or the `--adapter` argument set in a dbt command passed to `dbtenv --execute`.
- The execute command's `--dbt` argument can now take either a dbt version (e.g. 1.0.0) or full pip specifier to use (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.
- dbtenv's version command and config files can now use a dbt version (e.g. 1.0.0) or full pip specifier to use (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.

### Changed
- Dropped support for Homebrew.
- Previously created environments through dbtenv 1.0.0 will be ignored.
- dbtenv's default behaviour is now to install missing dbt adapter versions automatically. It can be disabled by setting the `DBTENV_AUTO_INSTALL` environment variable to `false`.
- Attempting to install a version of dbt which doesn't exist will exit cleanly, and provide a list of available versions for that adapter.
- Failed dbt version installations exit cleanly, removing the created virtual environment.

### Fixed
- Only entries in the environment directory which are dbtenv 2.0.0 environments will be read as installed dbt versions, fixing an issue where dbtenv 1.0.0 environments caused a failure.
- Fixed version command, and all dbtenv config files. These can now take either a dbt version (e.g. 1.0.0) or full pip specifier to use (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.

## [2.0.0a2](https://github.com/brooklyn-data/dbtenv/compare/v2.0.0a1...v2.0.0a2)

### Added
- The execute command's `--dbt` argument can now take either a dbt version (e.g. 1.0.0) or full pip specifier to use (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.

### Changed
- Attempting to install a version of dbt which doesn't exist will exit cleanly, and provide a list of available versions for that adapter.
- Failed dbt version installations exit cleanly, removing the created virtual environment.
- Improved logging.

### Fixed
- Only entries in the environment directory which are dbtenv 2.0.0 environments will be read as installed dbt versions, fixing an issue where dbtenv 1.0.0 environments caused a failure.
- Fixed version command, and all dbtenv config files. These can now take either a dbt version (e.g. 1.0.0) or full pip specifier to use (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.

## [2.0.0a1](https://github.com/brooklyn-data/dbtenv/compare/v1.3.2...v2.0.0a1)

### Added
- dbtenv now operates at the adapter-version level, introduced by dbt in version 1.0.0. The interface is identical to prior versions, dbtenv will automatically detect the needed adapter version from `profiles.yml`, or the `--adapter` argument set in a dbt command passed to `dbtenv --execute`.

### Changed
- Dropped support for Homebrew.
- Previously created environments through dbtenv cannot be used, and will be recreated by dbtenv at the adapter-version level.
- dbtenv's default behaviour is to install missing dbt adapter versions automatically. It can be disabled by setting the `DBTENV_AUTO_INSTALL` environment variable to `false`.

### Fixed

## [1.3.2](https://github.com/brooklyn-data/dbtenv/compare/v1.3.1...v1.3.2)

### Added

### Changed

### Fixed
- Remove Python 3.7 classifier from pyproject.toml

## [1.3.1](https://github.com/brooklyn-data/dbtenv/compare/v1.3.0...v1.3.1) - 2021-12-04

### Added
- Gracefully abort when dbt versions >= 1.0.0 attempted to install through Homebrew

### Changed

## [1.3.0](https://github.com/brooklyn-data/dbtenv/compare/v1.2.0...v1.3.0) - 2021-12-04

### Added
- Support for dbt 1.0.0 using pip.

### Changed
- Use Poetry for local development and builds.
- Require Python >= 3.8

## [1.2.0](https://github.com/brooklyn-data/dbtenv/compare/v1.1.1...v1.2.0) - 2021-11-29

### Added
- New `--quiet` argument to not output any nonessential information as dbtenv runs.
- Allow location of dbt version-specific Python virtual environments to be configured with `DBTENV_VENVS_DIRECTORY` and `DBTENV_VENVS_PREFIX` environment variables.
- Publish dbtenv package to PyPI.

### Changed
- If no specific dbt version has been selected then default to using the max installed version (if any) or the max installable version (preferring stable versions).
- If no compatible dbt version can be found for a dbt project and its installed packages then ignore dbt version requirements from installed packages in case they're simply out of date.
- When installing with pip, upgrade pip to avoid problems with packages that might require newer pip features.
- When installing with Homebrew, automatically add the dbt Homebrew tap if necessary.
- Switch from distutils to setuptools.


## [1.1.1](https://github.com/brooklyn-data/dbtenv/compare/v1.1.0...v1.1.1) - 2021-07-15

### Fixed
- Fix error when `~/.dbt/versions` directory doesn't exist yet.


## [1.1.0](https://github.com/brooklyn-data/dbtenv/compare/v1.0.0...v1.1.0) - 2021-07-14

### Added
- Support installation of dbt versions >= 0.20.0 in a Python 3.9 environment.


## [1.0.0](https://github.com/brooklyn-data/dbtenv/releases/tag/v1.0.0) - 2021-04-16

### Added
- Initial release
