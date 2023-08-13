import os
import subprocess
import venv

import typer
import yaml
from dotenv import load_dotenv

app = typer.Typer()


CONFIG_FILENAME = "config.yaml"


def create_project(config_path: str):
    # Create the project directory structure
    os.makedirs(config_path, exist_ok=True)
    dags_dir = os.path.join(config_path, "dags")
    os.makedirs(dags_dir, exist_ok=True)

    airflow_version = "2.6.0"
    python_version = "3.10"
    # Initialize the config file
    config_file = os.path.join(config_path, CONFIG_FILENAME)
    if not os.path.exists(config_file):
        default_config = {
            "python_version": python_version,
            "airflow_version": airflow_version,
            "constraints_url": "",
            "environment_variables": {},
            "variables": {},
            "connections": {},
        }
        with open(config_file, "w") as f:
            yaml.dump(default_config, f)

    typer.echo(f"Airflow project initialized in {config_path}")


@app.command()
def init(
    project_name: str = typer.Argument(
        default=".",
        help="Name of the Airflow project to be initialized.",
    )
):
    """
    Initialize a new Airflow project.
    """
    create_project(project_name)


def create_virtual_env(venv_path: str, python_version: str):
    venv.create(venv_path, with_pip=True, prompt="airflowctl")
    venv_bin_python = os.path.join(venv_path, "bin", "python")
    subprocess.run([venv_bin_python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])


def install_airflow(venv_path: str, constraints_url: str):
    venv_bin_python = os.path.join(venv_path, "bin", "python")
    subprocess.run(
        [venv_bin_python, "-m", "pip", "install", "apache-airflow", "--constraint", constraints_url]
    )


def create_env_file(project_path: str):
    env_file_path = os.path.join(project_path, ".env")
    with open(env_file_path, "w") as env_file:
        env_file.write(f"AIRFLOW_HOME={project_path}\n")


@app.command()
def build(
    project_path: str = typer.Argument(..., help="Absolute path to the Airflow project directory."),
):
    project_path = os.path.abspath(project_path)
    config_file = os.path.join(project_path, "config.yaml")

    if not os.path.exists(config_file):
        typer.echo(f"Config file '{config_file}' not found.")
        raise typer.Exit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    airflow_version = config.get("airflow_version")
    python_version = config.get("python_version")
    constraints_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-{airflow_version}/constraints-{python_version}.txt"

    venv_path = os.path.join(
        project_path, config.get("venv_path", f".venv/airflow_{airflow_version}_py{python_version}")
    )
    # Create virtual environment
    create_virtual_env(venv_path, python_version)

    # Install Airflow and dependencies
    install_airflow(venv_path, constraints_url)

    # Create .env file with AIRFLOW_HOME set to project directory
    create_env_file(project_path)

    typer.echo("Airflow project built successfully.")


PROJECTS_DB_FILE = os.path.expanduser("~/.airflowctl_projects.yaml")


def load_projects():
    if os.path.exists(PROJECTS_DB_FILE):
        with open(PROJECTS_DB_FILE) as f:
            projects = yaml.safe_load(f)
            return projects
    return {}


@app.command("list")
def list_cmd():
    projects = load_projects()

    if not projects:
        typer.echo("No projects found.")
        return

    typer.echo("List of projects:")
    for name, path in projects.items():
        typer.echo(f"{name}: {path}")


def source_env_file(env_file: str):
    try:
        load_dotenv(env_file)
    except Exception as e:
        typer.echo(f"Error loading .env file: {e}")
        raise typer.Exit(1)


def activate_virtualenv(venv_path: str):
    if os.name == "posix":
        bin_path = os.path.join(venv_path, "bin", "activate")
        activate_cmd = f"source {bin_path}"
    elif os.name == "nt":
        bin_path = os.path.join(venv_path, "Scripts", "activate")
        activate_cmd = f"call {bin_path}"
    else:
        typer.echo("Unsupported operating system.")
        raise typer.Exit(1)

    return activate_cmd


@app.command()
def start(
    project_path: str = typer.Argument(..., help="Absolute path to the Airflow project directory."),
):
    config_file = os.path.join(project_path, "config.yaml")
    env_file = os.path.join(project_path, ".env")

    if not os.path.exists(config_file):
        typer.echo(f"Config file '{config_file}' not found.")
        raise typer.Exit(1)

    if not os.path.exists(env_file):
        typer.echo(".env file not found.")
        raise typer.Exit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Source the .env file to set environment variables
    source_env_file(env_file)
    os.environ["AIRFLOW_HOME"] = project_path
    os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = "sqlite:///" + os.path.abspath(
        os.path.join(project_path, "airflow.db")
    )
    venv_path = os.path.abspath(config.get("venv_path", os.path.join(project_path, ".venv/airflow")))
    activate_cmd = activate_virtualenv(venv_path)

    try:
        # Activate the virtual environment and then run the airflow command
        subprocess.run(f"{activate_cmd} && airflow standalone", shell=True, check=True, env=os.environ)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error starting Airflow: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
