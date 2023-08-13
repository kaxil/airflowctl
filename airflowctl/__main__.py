import os
import subprocess
import sys
import venv
from pathlib import Path

import httpx
import typer
import yaml
from dotenv import load_dotenv
from rich import print

app = typer.Typer()

CONFIG_FILENAME = ".airflowctl/config.yaml"


def create_project(project_name: str, airflow_version: str, python_version: str):
    # Create the project directory
    project_dir = Path(project_name).absolute()
    project_dir.mkdir(exist_ok=True)

    # if directory is not empty, prompt user to confirm
    if any(project_dir.iterdir()):
        typer.confirm(
            f"Directory {project_dir} is not empty. Continue?",
            abort=True,
        )

    # Create the dags directory
    dags_dir = Path(project_dir / "dags")
    dags_dir.mkdir(exist_ok=True)

    # Copy the example dags from dags directory
    from_dir = Path(__file__).parent / "dags"
    for file in from_dir.iterdir():
        # Ignore if file exists
        if (dags_dir / file.name).exists():
            continue
        to_file = Path(dags_dir / file.name)
        to_file.write_text(file.read_text())

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
logs
.DS_Store
__pycache__/
.env
.venv
.airflowctl
""".strip()
        )

    # Initialize the settings file
    settings_file = Path(project_dir / "settings.yaml")
    if not settings_file.exists():
        file_contents = f"""
# Airflow version to be installed
airflow_version: {airflow_version}
# Python version for the project
python_version: "{python_version}"

# Airflow conn
connections: {{}}
# Airflow vars
variables: {{}}
        """
        settings_file.write_text(file_contents.strip())

    typer.echo(f"Airflow project initialized in {project_dir}")


def get_latest_airflow_version(verbose: bool = False) -> str:
    try:
        with httpx.Client() as client:
            response = client.get("https://pypi.org/pypi/apache-airflow/json")
            data = response.json()
            latest_version = data["info"]["version"]
            if verbose:
                print(f"Latest Apache Airflow version detected: [bold cyan]{latest_version}[/bold cyan]")
            return latest_version
    except (httpx.RequestError, KeyError) as e:
        if verbose:
            print(f"[bold red]Error occurred while retrieving latest version: {e}[/bold red]")
            print("[bold yellow]Defaulting to Apache Airflow version 2.7.0[/bold yellow]")
        return "2.7.0"


@app.command()
def init(
    project_name: str = typer.Argument(default=".", help="Name of the Airflow project to be initialized."),
    airflow_version: str = typer.Option(
        default=get_latest_airflow_version(verbose=True),
        help="Version of Apache Airflow to be used in the project. Defaults to latest.",
    ),
    python_version: str = typer.Option(
        default=f"{sys.version_info.major}.{sys.version_info.minor}",
        help="Version of Python to be used in the project.",
    ),
):
    """
    Initialize a new Airflow project.
    """
    create_project(project_name, airflow_version, python_version)


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

    venv_path = os.path.abspath(
        config.get(
            "venv_path",
            os.path.join(
                project_path,
                f".venv/airflow_{config.get('airflow_version')}_py{config.get('python_version')}",
            ),
        )
    )
    activate_cmd = activate_virtualenv(venv_path)

    try:
        # Activate the virtual environment and then run the airflow command
        subprocess.run(f"{activate_cmd} && airflow standalone", shell=True, check=True, env=os.environ)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error starting Airflow: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
