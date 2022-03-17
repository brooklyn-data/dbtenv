# dbtenv

dbtenv is a version manager for dbt, automatically installing and switching to the needed adapter and version of [dbt](https://docs.getdbt.com/docs/introduction).


## Installation

1. Install [pipx](https://pypa.github.io/pipx/) if you haven't already.
2. Run `pipx install dbtenv`.


## How it works

Run `dbtenv --help` to see some overall documentation for dbtenv, including its available sub-commands, and run `dbtenv <sub-command> --help` to see documentation for that sub-command.

dbtenv uses [pip](https://pip.pypa.io/) to install dbt versions from the [Python Package Index](https://pypi.org/project/dbt/#history) into Python virtual environments within `~/.dbt/versions`.

### Installing dbt versions
You can run `dbtenv versions` to list the versions of dbt available to install, and run `dbtenv install <version>` to install a specific version.

dbtenv will automatically install the required version of dbt for the current project by default. To disable this behaviour, set the environment variable `DBTENV_AUTO_INSTALL` to `false`.

Some tips:
- You can customize where the dbt package-version-specific Python virtual environments are created by setting the `DBTENV_VENVS_DIRECTORY` environment variable.
- You can have dbtenv only install Python packages that were actually available on the date the dbt version was released by setting a `DBTENV_SIMULATE_RELEASE_DATE=true` environment variable, or specifying `--simulate-release-date` when running `dbtenv install`.
  This can help if newer versions of dbt's dependencies are causing installation problems.
- By default dbtenv uses whichever Python version it was installed with to install dbt, but that can be changed by setting a `DBTENV_PYTHON` environment variable to the path of a different Python executable, or specifying `--python <path>` when running `dbtenv install`.

### Switching between dbt versions
#### Adapter type
If a dbtenv command is invoked from within a dbt project, dbtenv will try to determine the in-use adapter from the default set for the project's profile in `profiles.yml`. If the `--adapter` argument is set in the dbt command passed to `dbtenv execute`, dbtenv will use that adapter's type instead.

#### dbt version

dbtenv determines which dbt version to use by trying to read it from the following sources, in this order, using the first one it finds:

1. The `dbtenv execute` command's optional `--dbt <version>` argument.
2. A `DBT_VERSION` environment variable.
3. A `.dbt_version` file in the dbt project directory.
4. The [dbt version requirements](https://docs.getdbt.com/reference/project-configs/require-dbt-version/) of the dbt project and any dbt packages it uses.
   - If the dbt version requirements specify a range of versions rather than an exact version, then dbtenv will try to read a preferred dbt version from the sources below and will use that version if it's compatible with the requirements.
5. The first `.dbt_version` file found by searching the dbt project's parent directories.
6. The `~/.dbt/version` file.
7. The max installed dbt version (preferring stable versions).
8. The max installable dbt version (preferring stable versions).

You can:
- Run `dbtenv version` to show which dbt version dbtenv determines dynamically based on the current environment.
- Run `dbtenv which` to show the full path to the executable of the dbt version dbtenv determines dynamically based on the current environment.
- Run `dbtenv version --global <version>` to set the dbt version globally in the `~/.dbt/version` file.
- Run `dbtenv version --local <version>` to set the dbt version for the current directory in a `.dbt_version` file.

### Running dbt through dbtenv
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

Note that after adding such a `dbt` alias/function to your shell profile you'll need to reload the profile to activate it (e.g. by running `. ~/.bash_profile` in bash, or `. $PROFILE` in PowerShell).

### Uninstalling dbt versions
You can run `dbtenv versions --installed` to list the versions of dbt that dbtenv has installed in Python virtual environments and/or with Homebrew, and then run `dbtenv uninstall <version>` to uninstall a version.


## Development

### Development setup
1. Clone this repository onto your computer.
2. Install Poetry `pipx install poetry` ([What is pipx?](https://www.google.com/search?q=pipx&rlz=1C5GCEM_enGB953GB953&oq=Pipx&aqs=chrome.0.69i59i512j0i512l2j69i59j0i512l2j69i60l2.1010j0j7&sourceid=chrome&ie=UTF-8))
3. Install this project into a virtual environment `poetry install`
4. Activate the virtual environment `poetry shell`
5. Any `dbtenv` commands will run using the local version of the project.
