# Standard library
import argparse
import glob
import os.path
import re
import traceback
from typing import Collection, List, Optional

# External Libraries
import yaml

# Local
import dbtenv
from dbtenv import Args, DbtenvError, Environment, Subcommand, Version
import dbtenv.install
import dbtenv.versions


logger = dbtenv.LOGGER


class VersionSubcommand(Subcommand):
    """Show the dbt version automatically detected from the environment, or show/set the dbt version in a specific context."""

    name = 'version'

    def add_args_parser(self, subparsers: argparse._SubParsersAction, parent_parsers: List[argparse.ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            parents=parent_parsers,
            description="""
                Show the dbt version automatically detected from the environment, show/set the dbt version globally
                or for the local directory, or show the dbt version for the current dbt project or shell.
            """,
            help=self.__doc__
        )
        scope_group = parser.add_mutually_exclusive_group()
        scope_group.add_argument(
            '--global',
            dest='global_dbt_version',
            nargs='?',
            type=str,
            const='',
            metavar='<dbt_version>',
            help=f"Show/set the dbt version globally using the `{dbtenv.GLOBAL_VERSION_FILE}` file."
        )
        scope_group.add_argument(
            '--local',
            dest='local_dbt_version',
            nargs='?',
            type=str,
            const='',
            metavar='<dbt_version>',
            help=f"Show/set the dbt version for the local directory using `{dbtenv.LOCAL_VERSION_FILE}` files."
        )
        scope_group.add_argument(
            '--project',
            dest='project_dbt_version',
            action='store_const',
            const=True,
            help=f"Show the dbt version determined for the current dbt project based on its dbt version requirements."
        )
        scope_group.add_argument(
            '--shell',
            dest='shell_dbt_version',
            action='store_const',
            const=True,
            help=f"Show the dbt version set for the current shell using a {dbtenv.DBT_VERSION_VAR} environment variable."
        )

    def execute(self, args: Args) -> None:
        if args.global_dbt_version is not None:
            if args.global_dbt_version != '':
                if bool(re.search(r"^(dbt-.+)==(.+)$", args.global_dbt_version)):
                    version = Version(pip_specifier=args.global_dbt_version)
                    dbtenv.install.ensure_dbt_is_installed(self.env, version)
                    set_global_version(self.env, version.pip_specifier)
                elif bool(re.search(r"^[0-9\.]+[a-z0-9]*$", args.global_dbt_version)):
                    set_global_version(self.env, args.global_dbt_version)
                else:
                    logger.info("Argument value doesn't match a dbt version (e.g. 1.0.0) or full pip specifier (e.g. dbt-snowflake==1.0.0).")
                    return
            else:
                global_version = try_get_global_version(self.env)
                if global_version:
                    print(global_version)
                else:
                    logger.info(f"No global dbt version has been set using the `{dbtenv.GLOBAL_VERSION_FILE}` file.")
        elif args.local_dbt_version is not None:
            if args.local_dbt_version != '':
                if bool(re.search(r"^(dbt-.+)==(.+)$", args.local_dbt_version)):
                    version = Version(pip_specifier=args.local_dbt_version)
                    dbtenv.install.ensure_dbt_is_installed(self.env, version)
                    set_local_version(self.env, version.pip_specifier)
                elif bool(re.search(r"^[0-9\.]+[a-z0-9]*$", args.local_dbt_version)):
                    set_local_version(self.env, args.local_dbt_version)
                else:
                    logger.info("Argument value doesn't match a dbt version (e.g. 1.0.0) or full pip specifier (e.g. dbt-snowflake==1.0.0).")
                    return
            else:
                local_version = try_get_local_version(self.env)
                if local_version:
                    print(f"{local_version}  ({local_version.source_description})")
                else:
                    logger.info(f"No local dbt version has been set for `{self.env.working_directory}` using `{dbtenv.LOCAL_VERSION_FILE}` files.")
        elif args.project_dbt_version is not None:
            if self.env.project_directory:
                shell_version = try_get_shell_version(self.env)
                local_version = try_get_local_version(self.env)
                global_version = try_get_global_version(self.env)
                preferred_version = shell_version or local_version or global_version
                project_version = try_get_project_version(self.env, preferred_version)
                if project_version:
                    if preferred_version and project_version == preferred_version:
                        logger.info(
                            f"Preferred version {preferred_version} ({preferred_version.source_description}) is compatible"
                            " with all version requirements in the dbt project."
                        )
                    print(f"{project_version}  ({project_version.source_description})")
                # If no project version could be determined, try_get_project_version() will have already logged the reason why.
            else:
                logger.error("No dbt project found.")
        elif args.shell_dbt_version is not None:
            shell_version = try_get_shell_version(self.env)
            if shell_version:
                print(shell_version)
            else:
                logger.info(f"No dbt version has been set for the current shell using a {dbtenv.DBT_VERSION_VAR} environment variable.")
        else:
            version = get_version(self.env)
            if version:
                print(f"{version}  ({version.source_description})")


def read_version_file(file_path: str, adapter_type: Optional[str], source_description: str) -> Optional[Version]:
    with open(file_path, 'r') as file:
        value = file.readline().strip()
        if bool(re.search(r"^(dbt-.+)==(.+)$", value)):
            return Version(pip_specifier=value, source_description=source_description)
        elif bool(re.search(r"^[0-9\.]+[a-z0-9]*$", value)):
            if adapter_type:
                return Version(adapter_type=adapter_type, version=value, source_description=source_description)
        else:
            raise(DbtenvError(f"Invalid value in {file_path}: {value}"))

def write_version_file(file_path: str, value: str) -> None:
    with open(file_path, 'w') as file:
        file.write(str(value))


def try_get_global_version(env: Environment, adapter_type: Optional[str]) -> Optional[Version]:
    if os.path.isfile(env.global_version_file):
        return read_version_file(env.global_version_file, adapter_type, f"set by global version file {env.global_version_file}")
    else:
        return None


def set_global_version(env: Environment, value: str) -> None:
    write_version_file(env.global_version_file, value)
    logger.info(f"{value} is now set as the global dbt version in `{env.global_version_file}`.")


def try_get_local_version(env: Environment, adapter_type: Optional[str]) -> Optional[Version]:
    version_file = env.find_file_along_working_path(dbtenv.LOCAL_VERSION_FILE)
    if version_file:
        return read_version_file(version_file, adapter_type, f"set by local version file {version_file}")
    else:
        return None


def set_local_version(env: Environment, value: str) -> None:
    version_file = os.path.join(env.working_directory, dbtenv.LOCAL_VERSION_FILE)
    write_version_file(version_file, value)
    logger.info(f"{value} is now set as the local dbt version in `{version_file}`.")


def try_get_shell_version(env: Environment, adapter_type: Optional[str]) -> Optional[Version]:
    if dbtenv.DBT_VERSION_VAR in env.env_vars:
        value = env.env_vars[dbtenv.DBT_VERSION_VAR]
        if bool(re.search(r"^(dbt-.+)==(.+)$", value)):
            return Version(pip_specifier=value)
        elif bool(re.search(r"^[0-9\.]+[a-z0-9]*$", value)):
            if adapter_type:
                return Version(adapter_type=adapter_type, version=value)
        else:
            raise(DbtenvError(f"Invalid value in {dbtenv.DBT_VERSION_VAR} environment variable: {value}"))


class VersionRequirement:
    def __init__(self, adapter_type: str, requirement: str, source: str) -> None:
        self.requirement = requirement
        requirement_match = re.match(r'(?P<operator>[<>=]=?)?(?P<version>.+)', requirement)
        self.operator = requirement_match['operator'] or '=='
        self.version = Version(adapter_type=adapter_type, version=requirement_match['version'])
        self.source = source

    def __str__(self) -> str:
        return self.requirement

    def is_compatible_with(self, version: Version) -> bool:
        if self.operator == '<':
            return version < self.version
        elif self.operator == '<=':
            return version <= self.version
        elif self.operator == '>':
            return version > self.version
        elif self.operator == '>=':
            return version >= self.version
        else:
            return version == self.version


def try_get_project_version_requirements(project_file: str, adapter_type: str) -> List[VersionRequirement]:
    try:
        with open(project_file) as file:
            project_file_yml = yaml.safe_load(file)

        requirements = project_file_yml.get("require-dbt-version")
        if requirements:
            if isinstance(requirements, str):
                requirements = requirements.split(',')
            return [VersionRequirement(adapter_type, requirement.strip(), project_file) for requirement in requirements]
    except Exception as error:
        logger.error(f"Error getting dbt version requirements from `{project_file}`:  {error}")
        logger.debug(traceback.format_exc())

    return []


def get_max_version(versions: Collection[Version]) -> Version:
    stable_versions = [version for version in versions if version.is_stable]
    if stable_versions:
        return sorted(stable_versions)[-1]
    else:
        return sorted(versions)[-1]


def try_get_max_compatible_version(versions: Collection[Version], requirements: Collection[VersionRequirement]) -> Optional[Version]:
    compatible_versions = [
        version
        for version in versions
        if version.is_semantic and all(requirement.is_compatible_with(version) for requirement in requirements)
    ]
    if compatible_versions:
        return get_max_version(compatible_versions)
    else:
        return None

def try_get_project_adapter_type(project_file: str, target_name: Optional[str] = None) -> Optional[str]:
    if not project_file:
        return
    with open(project_file) as file:
        dbt_project_yml = yaml.safe_load(file)

    profile_name = dbt_project_yml["profile"]

    home = os.path.expanduser("~")
    with open(os.path.join(home, ".dbt", "profiles.yml")) as file:
        profiles_yml = yaml.safe_load(file)

    if not target_name:
        target_name = profiles_yml.get(profile_name, {}).get("target")
    adapter_type = profiles_yml.get(profile_name, {}).get("outputs", {}).get(target_name, {}).get("type")
    if not adapter_type:
        logger.info("Could not determine adapter type as no default target is set for the current project in profiles.yml.")
    return adapter_type


def try_get_project_version(env: Environment, preferred_version: Optional[Version] = None, adapter_type: Optional[str] = None) -> Optional[Version]:
    project_version_requirements = try_get_project_version_requirements(env.project_file, adapter_type)
    if not project_version_requirements:
        logger.debug(f"The dbt project has no version requirements.")
        return None

    all_version_requirements = project_version_requirements.copy()
    project_file = os.path.basename(env.project_file)
    requirements_project_files = [project_file]
    scope_decription = "the dbt project"

    if preferred_version:
        for requirement in all_version_requirements:
            if not requirement.is_compatible_with(preferred_version):
                logger.info(
                    f"Preferred version {preferred_version} ({preferred_version.source_description}) is incompatible with"
                    f" the {requirement} requirement in `{os.path.relpath(requirement.source, env.project_directory)}`."
                )
                break
        else:
            return preferred_version

    installed_versions = dbtenv.versions.get_installed_versions(env, adapter_type=adapter_type)
    compatible_version = try_get_max_compatible_version(installed_versions, all_version_requirements)
    if compatible_version:
        compatible_version.source = ', '.join(requirements_project_files)
        return compatible_version

    installable_versions = dbtenv.versions.get_installable_versions(env, adapter_type=adapter_type)
    compatible_version = try_get_max_compatible_version(installable_versions, all_version_requirements)
    if compatible_version:
        logger.info(f"{compatible_version} is the latest installable version that is compatible with all version requirements in {scope_decription}.")
        compatible_version.source = ', '.join(requirements_project_files)
        return compatible_version

    warning = f"No available versions are compatible with all version requirements in {scope_decription}."
    logger.warning(warning)

    return None


def get_version(env: Environment, adapter_type: Optional[str] = None) -> Optional[Version]:
    if not adapter_type:
        adapter_type = dbtenv.version.try_get_project_adapter_type(env.project_file)

    shell_version = try_get_shell_version(env, adapter_type)
    if shell_version:
        return shell_version

    local_version = try_get_local_version(env, adapter_type)
    if local_version and (not env.project_directory or local_version.source.startswith(env.project_directory)):
        return local_version

    global_version = try_get_global_version(env, adapter_type)
    if global_version and not env.project_directory:
        return global_version

    # All below options require an already known adapter type
    if not adapter_type:
        logger.info("Could not determine adapter type as no dbt --target arg specified, not running in dbt project with a default target, and no full pip specifier set in dbtenv's configuration.")
        return None

    preferred_version = local_version or global_version
    if env.project_directory:
        project_version = try_get_project_version(env, preferred_version, adapter_type)
        if project_version:
            return project_version

    if preferred_version:
        return preferred_version

    installed_versions = dbtenv.versions.get_installed_versions(env, adapter_type=adapter_type)
    if installed_versions:
        max_installed_version = get_max_version(installed_versions)
        return Version(adapter_type=adapter_type, version=max_installed_version.pypi_version, source_description="max installed stable version for current adapter")

    installable_versions = dbtenv.versions.get_installable_versions(env, adapter_type=adapter_type)
    max_installable_version = get_max_version(installable_versions)
    max_installable_version.source_description = "max installable stable version for current adapter"
    return max_installable_version
