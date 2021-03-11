# dbtenv

dbtenv lets you easily install and run multiple versions of [dbt](https://docs.getdbt.com/docs/introduction) in dedicated [Python virtual environments](https://docs.python.org/3/library/venv.html).

### Table of contents
- **[Installation](#installation)**
- **[How it works](#how-it-works)**
  - [Installing dbt versions](#installing-dbt-versions)
  - [Switching between dbt versions](#switching-between-dbt-versions)
  - [Running dbt versions](#running-dbt-versions)
  - [Running dbt with dbtenv more seamlessly](#running-dbt-with-dbtenv-more-seamlessly)
  - [Uninstalling dbt versions](#uninstalling-dbt-versions)
- **[Development](#development)**
  - [Development setup](#development-setup)


## Installation
TBD


## How it works

### Installing dbt versions
You can run `dbtenv versions` to list the versions of dbt available to install from the [Python Package Index](https://pypi.org/project/dbt/#history), and then run `dbtenv install <version>` to manually install a version, or use dbtenv's auto-install feature by setting a `DBTENV_AUTO_INSTALL` environment variable to `true` or specifying `--auto-install` when running `dbtenv version` or `dbtenv execute`.

Notes:
- The dbt version-specific Python virtual environments are created under `~/.dbt/versions`.
- By default dbtenv uses whichever Python version it was installed with to install dbt, but that can be changed by setting a `DBTENV_PYTHON` environment variable to the path of a different Python executable, or specifying `--python <path>` when running `dbtenv install`.

**Important:**  dbt currently isn't compatible with Python 3.9 or above, so if dbtenv was installed with Python 3.9 or above you will need to specify a compatible Python version to install dbt.

### Switching between dbt versions
dbtenv determines which dbt version to use by trying to read it from the following sources, in this order, using the first one it finds:

1. The `dbtenv execute` command's optional `--dbt <version>` argument.
2. The `DBT_VERSION` environment variable.
3. The first `.dbt_version` file found by searching in the current directory and then in each successive parent directory.
4. The `~/.dbt/version` file.

You can:
- Run `dbtenv version --global <version>` to set the dbt version globally in the `~/.dbt/version` file.
- Run `dbtenv version --local <version>` to set the dbt version for the current directory in a `.dbt_version` file.
- Run `dbtenv version` to show which dbt version dbtenv determines dynamically based on the current environment.

### Running dbt versions
Run `dbtenv execute -- <dbt arguments>` to execute the dbt version determined dynamically based on the current environment, or run `dbtenv execute --dbt <version> -- <dbt arguments>` to execute the specified dbt version.

For example:
- `dbtenv execute -- run` will execute `dbt run` using the version determined dynamically based on the current environment.
- `dbtenv execute --dbt 0.19.0 -- run` will execute `dbt run` using dbt 0.19.0.

**Important:**  It's highly recommended to put two dashes with spaces on both sides before the list of dbt arguments (as shown in the examples above) so that dbtenv doesn't try to interpret the dbt arguments itself.

### Running dbt with dbtenv more seamlessly
For a more seamless experience you can define a `dbt` alias or function in your shell to run `dbtenv execute -- <dbt arguments>` and dynamically determine which dbt version to use whenever you type dbt commands like `dbt run` or `dbt test`.

Some examples:
- In **bash** you could add the following alias in your `~/.bash_profile` file:
  ```bash
  alias dbt='dbtenv execute --'
  ```
- In **Windows PowerShell** aliases can't include additional arguments, but you could add the following function in your `~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` file:
  ```PowerShell
  function dbt { dbtenv execute -- @Args }
  ```

Tips:
- After adding such a `dbt` alias/function to your shell profile you'll need to reload the profile to activate it (e.g. `. ~/.bash_profile` in bash, or `. $PROFILE` in PowerShell).
- For an even more seamless experience use `dbtenv execute --auto-install --` in your alias/function so that any dbt version specified that isn't already installed will be installed automatically.

### Uninstalling dbt versions
You can run `dbtenv versions --installed` to list the versions of dbt that dbtenv has installed under `~/.dbt/versions`, and then run `dbtenv uninstall <version>` to uninstall a version.


## Development

### Development setup
1. Clone this repository onto your computer.
2. If you want to isolate the dbtenv development setup (e.g. because you have dbtenv installed normally), create and activate a [Python virtual environment](https://docs.python.org/3/library/venv.html).
3. Run `pip install --editable <path to cloned repo>`.
