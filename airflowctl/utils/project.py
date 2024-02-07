from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import typer
import yaml
from rich import print

from airflowctl.utils.install_airflow import get_airflow_versions, get_latest_airflow_version

INSTALLED_PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def copy_example_dags(project_path: Path):
    from_dir = Path(__file__).parent.parent / "dags"
    assert from_dir.exists()

    to_dir = project_path / "dags"
    if to_dir.exists():
        # Skip if dags directory already exists
        return

    # Create the dags directory
    to_dir.mkdir(exist_ok=True)

    # Copy *.py files from example dags directory
    for file in from_dir.iterdir():
        if file.suffix == ".py":
            shutil.copy(file, to_dir)


def create_project(
    project_name: str,
    project_path: str | Path,
    airflow_version: str,
    python_version: str,
    venv_path: str | Path = None,
) -> tuple[Path, Path]:
    # Create a config directory for storing internal state and settings
    GLOBAL_CONFIG_DIR.mkdir(exist_ok=True)
    GLOBAL_TRACKING_FILE.touch(exist_ok=True)

    if not os.getenv("AIRFLOWCTL_SKIP_VERSION_CHECK"):
        available_airflow_vers = get_airflow_versions()
        if airflow_version not in available_airflow_vers and not Path(airflow_version).exists():
            print(f"Apache Airflow version [bold red]{airflow_version}[/bold red] not found.")
            print(f"Please select a valid version from the list below: {available_airflow_vers}")
            raise typer.Exit(code=1)

    # Create the project directory
    project_dir = Path(project_path).absolute()
    project_dir.mkdir(exist_ok=True)

    # if directory is not empty, prompt user to confirm
    if any(project_dir.iterdir()):
        typer.confirm(
            f"Directory {project_dir} is not empty. Continue?",
            abort=True,
        )

    # Track the project in the config file
    add_project_to_tracking(project_dir)

    # Create a config directory for storing internal state and settings for the project
    project_config_dir = project_dir / ".airflowctl"
    project_config_dir.mkdir(exist_ok=True)
    project_config_yaml = project_config_dir / "config.yaml"
    project_config_yaml.touch(exist_ok=True)

    if not project_name:
        project_name = str(project_dir)
    with project_config_yaml.open("w") as f:
        yaml.dump({"project_name": project_name}, f)

    # Create the dags directory
    copy_example_dags(project_dir)

    # Create the plugins directory
    plugins_dir = Path(project_dir / "plugins")
    plugins_dir.mkdir(exist_ok=True)

    # Create requirements.txt
    requirements_file = Path(project_dir / "requirements.txt")
    requirements_file.touch(exist_ok=True)

    # Create .gitignore
    gitignore_file = Path(project_dir / ".gitignore")
    gitignore_file.touch(exist_ok=True)
    with open(gitignore_file, "w") as f:
        f.write(
            """
.git
airflow.cfg
airflow.db
airflow-webserver.pid
webserver_config.py
logs
standalone_admin_password.txt
.DS_Store
__pycache__/
.env
.venv
.airflowctl
""".strip()
        )

    # Initialize the settings file
    settings_file = Path(project_dir / SETTINGS_FILENAME)

    # Check if the project is an Astro project and use the Astro settings file
    if is_astro_project(project_dir):
        settings_file = Path(project_dir / ASTRO_SETTINGS_FILENAME)

    venv_path = Path(venv_path).absolute() if venv_path else f"{project_dir}/.venv"
    if not settings_file.exists():
        file_contents = f"""
# Airflow version to be installed
airflow_version: "{airflow_version}"

# Python version for the project
python_version: "{python_version}"

# Path to a virtual evn
mode:
  virtualenv:
    venv_path: "{venv_path}"

# Airflow connections
connections:
    # Example connection
    # - conn_id: example
    #   conn_type: http
    #   host: http://example.com
    #   port: 80
    #   login: user
    #   password: pass
    #   schema: http
    #   extra:
    #      example_extra_field: example-value

# Airflow variables
variables:
    # Example variable
    # - key: example
    #   value: example-value
    #   description: example-description
        """
        settings_file.write_text(file_contents.strip())

    # Initialize the .env file
    env_file = Path(project_dir / ".env")
    if not env_file.exists():
        file_contents = f"""
AIRFLOW_HOME={project_dir}
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__CORE__FERNET_KEY=d6Vefz3G9U_ynXB3cr7y_Ak35tAHkEGAVxuz_B-jzWw=
AIRFLOW__WEBSERVER__WORKERS=2
AIRFLOW__WEBSERVER__SECRET_KEY=secret
AIRFLOW__WEBSERVER__EXPOSE_CONFIG=True
"""
        env_file.write_text(file_contents.strip())
    typer.echo(f"Airflow project initialized in {project_dir}")
    return project_dir, settings_file


def add_project_to_tracking(project_path: str | Path):
    """Add an Airflow project to tracking."""

    contents = GLOBAL_TRACKING_FILE.read_text()
    if not contents:
        contents = {"projects": []}
    else:
        contents = yaml.safe_load(contents)

    tracked_projects = contents.get("projects", [])
    project_path = str(Path(project_path).absolute())

    if project_path in tracked_projects:
        return

    contents["projects"].append(project_path)

    with open(GLOBAL_TRACKING_FILE, "w") as f:
        yaml.dump(contents, f)

    print(f"Project {project_path} added to tracking.")


def airflowctl_project_check(project_path: str | Path):
    """Check if the current directory is an Airflow project."""
    # Abort if .airflowctl directory does not exist in the project
    airflowctl_dir = Path(project_path) / ".airflowctl"
    if not airflowctl_dir.exists():
        print("Not an airflowctl project. Run 'airflowctl init' to initialize the project.")
        raise typer.Exit(1)


SETTINGS_FILENAME = "settings.yaml"
ASTRO_SETTINGS_FILENAME = "airflow_settings.yaml"
GLOBAL_CONFIG_DIR = Path.home() / ".airflowctl"
GLOBAL_TRACKING_FILE = GLOBAL_CONFIG_DIR / "tracked_projects.yaml"


def get_conf_or_raise(key: str, settings: dict) -> str:
    if key not in settings:
        typer.echo(f"Key '{key}' not found in settings file.")
        raise typer.Exit(1)
    return settings[key]


def is_astro_project(project_path: Path) -> bool:
    """Identify the Astro project."""
    astro_config_dir = project_path / ".astro"
    if astro_config_dir.exists() or (project_path / ASTRO_SETTINGS_FILENAME).exists():
        return True
    return False


def add_airflowctl_keys_to_astro_settings_file(astro_settings_file: Path):
    """Add airflowctl keys to the Astro settings file."""

    if not astro_settings_file.exists():
        return
    astro_settings = yaml.safe_load(astro_settings_file.read_text())

    if "airflow_version" in astro_settings and "python_version" in astro_settings:
        return

    if "airflow_version" not in astro_settings:
        latest_version = get_latest_airflow_version()
        if not typer.prompt(
            f"'airflow_version' not found in {ASTRO_SETTINGS_FILENAME} file."
            f" What is the Airflow version?",
            default=latest_version,
        ):
            raise typer.Exit(1)
        astro_settings["airflow_version"] = latest_version

    if "python_version" not in astro_settings:
        print("Python version not found in Astro settings file. Using the installed Python version.")
        astro_settings["python_version"] = INSTALLED_PYTHON_VERSION

    with astro_settings_file.open("w") as f:
        yaml.dump(astro_settings, f)


def get_settings_file_path_or_raise(
    project_path: Path,
    settings_file: Path | str | None = None,
    raise_if_not_found: bool = True,
    verbose: bool = True,
) -> Path:
    if isinstance(project_path, str):
        project_path = Path(project_path)

    if is_astro_project(project_path):
        settings_file = project_path / ASTRO_SETTINGS_FILENAME
        if verbose:
            typer.echo(f"Detected Astro project. Using Astro settings file ({settings_file}).")

        # Add airflow.db and airflow.cfg to .gitignore
        gitignore_file = project_path / ".gitignore"

        if gitignore_file.exists():
            gitignore_contents = gitignore_file.read_text()
            if "airflow.db" not in gitignore_contents:
                gitignore_contents += "\nairflow.db"
            if "airflow.cfg" not in gitignore_contents:
                gitignore_contents += "\nairflow.cfg"
            if ".venev" not in gitignore_contents:
                gitignore_contents += "\n.venv"
            gitignore_file.write_text(gitignore_contents)

        dockerignore_file = project_path / ".dockerignore"
        if dockerignore_file.exists():
            dockerignore_contents = dockerignore_file.read_text()
            if "airflow.db" not in dockerignore_contents:
                dockerignore_contents += "\nairflow.db"
            if "airflow.cfg" not in dockerignore_contents:
                dockerignore_contents += "\nairflow.cfg"
            if ".venev" not in dockerignore_contents:
                dockerignore_contents += "\n.venv"
            dockerignore_file.write_text(dockerignore_contents)

        add_airflowctl_keys_to_astro_settings_file(settings_file)

    if not settings_file:
        settings_file = project_path / SETTINGS_FILENAME
    settings_file = Path(settings_file).absolute()
    if not settings_file.exists() and raise_if_not_found:
        typer.echo(f"Settings file '{settings_file}' not found.")
        raise typer.Exit(1)
    return settings_file
