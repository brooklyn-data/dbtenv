# dbtenv Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/brooklyn-data/dbtenv/compare/v1.1.1...HEAD)

### Added

### Changed
- If no compatible dbt version can be found then ignore dbt version requirements from installed packages in case they're simply out of date.

## [1.1.1](https://github.com/brooklyn-data/dbtenv/compare/v1.1.0...v1.1.1) - 2021-07-15

### Fixed
- Fix error when `~/.dbt/versions` directory doesn't exist yet.

## [1.1.0](https://github.com/brooklyn-data/dbtenv/compare/v1.0.0...v1.1.0) - 2021-07-14

### Added
- Support installation of dbt versions >= 0.20.0 in a Python 3.9 environment.

## [1.0.0](https://github.com/brooklyn-data/dbtenv/releases/tag/v1.0.0) - 2021-04-16

### Added
- Initial release
