# dbtenv

dbtenv is a version manager for dbt, automatically installing and switching to the needed adapter and version of [dbt](https://docs.getdbt.com/docs/introduction).

## Quickstart
### Installation

1. Install [pipx](https://pypa.github.io/pipx/) ([What is pipx?](https://www.google.com/search?q=pipx&rlz=1C5GCEM_enGB953GB953&oq=Pipx&aqs=chrome.0.69i59i512j0i512l2j69i59j0i512l2j69i60l2.1010j0j7&sourceid=chrome&ie=UTF-8)).
2. Run `pipx install dbtenv[dbt-alias]`.

### Usage
If the `dbt-alias` extra is used (`dbtenv[dbt-alias]`), dbt commands can be used as normal and will be routed through dbtenv. dbtenv will automatically determine, install and use the required dbt adapter and version.

Illustrative example
```
dbt --version
dbtenv info:  Using dbt-bigquery==1.0.0 (set by dbt_project.yml).
installed version: 1.0.4
   latest version: 1.0.4

Up to date!

Plugins:
  - bigquery: 1.0.0 - Up to date!
```


## Available Commands

- `dbtenv --help` - Print documentation and available commands. Can also be run for information on a individual command, e.g. `dbtenv versions --help`.
- `dbtenv versions` - List the installable versions of dbt, marking those which are currently installed. Add the `--installed` flag to show only those which are installed.
- `dbtenv install <dbt_pip_specifier>` - Install a specific version of dbt, e.g. `dbtenv install dbt-snowflake==1.0.0`.
- `dbtenv uninstall <dbt_pip_specifier>` - Uninstall a specific version of dbt, e.g. `dbtenv uninstall dbt-snowflake==1.0.0`.
- `dbtenv version` - Print the dbt version dbtenv determines automatically for the current environment.
- `dbtenv which` - Print the full path to the executable of the dbt version dbtenv determines automatically for the current environment.
- `dbtenv execute` - Execute a dbt command.


## dbt Version Management
dbtenv will automatically install the required version of dbt for the current project by default. To disable this behaviour, set the environment variable `DBTENV_AUTO_INSTALL` to `false`.

By default, dbtenv creates virtual environments for each dbt package version within `~/.dbt/versions`. You can customize this location by setting the `DBTENV_VENVS_DIRECTORY` environment variable.

By default, dbtenv uses whichever Python version it was installed with to install dbt, but that can be changed by setting a `DBTENV_PYTHON` environment variable to the path of a different Python executable, or specifying `--python <path>` when running `dbtenv install`.

## Switching between dbt versions
### Adapter type
If dbtenv is invoked within a dbt project, dbtenv will look for the project's default target adapter type in `profiles.yml`. If dbt's `--target` argument is set, dbtenv will use that target's adapter type instead. To use the `dbtenv execute` command outside of a dbt project (such as `dbt init`), a pip specifier should be passed to dbtenv execute's `--dbt` argument so that dbtenv knows which adapter to use.

### dbt version

dbtenv determines the dbt version to use from the following sources, using the first one it finds:

1. The `dbtenv execute` command's optional `--dbt <version>` argument.
2. The `DBT_VERSION` environment variable.

3. If not running within a dbt project:
    1. The first `.dbt_version` file found searching the working directory path (local version).
    2. The `~/.dbt/version` file (global version).
4. The current dbt project's [dbt_project.yml](https://docs.getdbt.com/reference/project-configs/require-dbt-version/) version requirements.
   - If a local or global dbt version has been set, dbtenv will use that version if in the range set by `require-dbt-version`.
5. The locally or globally set version.
6. The max installed dbt version (preferring stable versions).
7. The max installable dbt version (preferring stable versions).

You can:
- Run `dbtenv version --global <version>` to set the dbt version globally in the `~/.dbt/version` file. The `<version>` can be either a dbt version (e.g. 1.0.0) or full pip specifier (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.
- Run `dbtenv version --local <version>` to set the dbt version for the current directory in a `.dbt_version` file. The `<version>` can be either a dbt version (e.g. 1.0.0) or full pip specifier (e.g. dbt-snowflake==1.0.0). dbtenv will attempt to automatically detect the required adapter or version from the environment if not specified.

## Running dbt through dbtenv

### dbt-alias

The `dbtenv-dbt-alias` package creates an entrypoint for the `dbt` command to route through dbtenv. The package is installable using the `[dbt-alias]` extra when installing dbtenv. The `dbt` command then acts as a direct shortcut to `dbtenv execute --`, and means that dbtenv can used as a drop-in replacement to installing dbt normally.

### dbtenv execute

Run `dbtenv execute -- <dbt arguments>` to execute the dbt version determined automatically from the current environment, or run `dbtenv execute --dbt <version> -- <dbt arguments>` to execute a specific dbt version.

For example:
- `dbtenv execute -- run` will execute `dbt run` using the version determined automatically from the current environment.
- `dbtenv execute --dbt 1.0.0 -- run` will execute `dbt run` using dbt 1.0.0, automatically detecting the required adapter from the default target in `profiles.yml`.
- `dbtenv execute --dbt 1.0.0 -- run --target prod` will execute `dbt run` using dbt 1.0.0, using the required adapter for the 'prod' target in `profiles.yml`.
- `dbtenv execute --dbt 1.0.0==dbt-bigquery -- run` will execute `dbt run` using dbt-bigquery==1.0.0.


## Development

### Development setup
1. Clone this repository onto your computer.
2. Install Poetry `pipx install poetry` ([What is pipx?](https://www.google.com/search?q=pipx&rlz=1C5GCEM_enGB953GB953&oq=Pipx&aqs=chrome.0.69i59i512j0i512l2j69i59j0i512l2j69i60l2.1010j0j7&sourceid=chrome&ie=UTF-8))
3. Navigate to the `dbtenv` directory, and install the project into a virtual environment `poetry install`
4. Activate the virtual environment `poetry shell`
5. Any `dbtenv` commands will run using the local version of the project.
