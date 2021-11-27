# dbtenv Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased](https://github.com/brooklyn-data/dbtenv/compare/v1.2.0...HEAD)

### Added

### Changed

### Fixed


## [1.2.0](https://github.com/brooklyn-data/dbtenv/compare/v1.1.1...v1.2.0) - 2021-11-29

### Added
- New `--quiet` argument to not output any nonessential information as dbtenv runs.
- Allow location of dbt version-specific Python virtual environments to be configured with `DBTENV_VENVS_DIRECTORY` and `DBTENV_VENVS_PREFIX` environment variables.

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
