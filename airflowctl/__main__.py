from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import httpx
import psutil
import typer
import yaml
from dotenv import load_dotenv
from rich import print

app = typer.Typer()

SETTINGS_FILENAME = "settings.yaml"


def copy_example_dags(project_path: Path):
    from_dir = Path(__file__).parent / "dags"
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


def create_project(project_name: str, airflow_version: str, python_version: str) -> tuple[Path, Path]:
    # Create a config directory for storing internal state and settings
    config_dir = Path.home() / ".airflowctl"
    config_dir.mkdir(exist_ok=True)

    available_airflow_vers = get_airflow_versions()
    if airflow_version not in available_airflow_vers:
        print(f"Apache Airflow version [bold red]{airflow_version}[/bold red] not found.")
        print(f"Please select a valid version from the list below: {available_airflow_vers}")
        raise typer.Exit(code=1)

    # Create the project directory
    project_dir = Path(project_name).absolute()
    project_dir.mkdir(exist_ok=True)

    # if directory is not empty, prompt user to confirm
    if any(project_dir.iterdir()):
        typer.confirm(
            f"Directory {project_dir} is not empty. Continue?",
            abort=True,
        )

    # Create a config directory for storing internal state and settings for the project
    project_config_dir = project_dir / ".airflowctl"
    project_config_dir.mkdir(exist_ok=True)

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


def get_airflow_versions(verbose: bool = False) -> list[str]:
    with httpx.Client() as client:
        response = client.get("https://pypi.org/pypi/apache-airflow/json")
        data = response.json()
        versions = list(data["releases"].keys())
        if verbose:
            print(f"Apache Airflow versions detected: [bold cyan]{versions}[/bold cyan]")
        return versions


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
    project_name: str = typer.Argument(
        ...,
        help="Name of the Airflow project to be initialized.",
    ),
    airflow_version: str = typer.Option(
        default=get_latest_airflow_version(),
        help="Version of Apache Airflow to be used in the project. Defaults to latest.",
    ),
    python_version: str = typer.Option(
        default=f"{sys.version_info.major}.{sys.version_info.minor}",
        help="Version of Python to be used in the project.",
    ),
    build_start: bool = typer.Option(
        default=False,
        help="Build the project and start after initialization.",
    ),
    background: bool = typer.Option(
        default=False,
        help="Run Airflow in the background.",
    ),
):
    """
    Initialize a new Airflow project.
    """
    project_dir, settings_file = create_project(project_name, airflow_version, python_version)
    if build_start:
        venv_path = Path(project_dir / ".venv")
        build(project_path=project_dir, settings_file=settings_file, venv_path=venv_path, recreate_venv=False)
        start(project_path=project_dir, venv_path=venv_path, background=background)


def verify_or_create_venv(venv_path: str | Path, recreate: bool):
    venv_path = os.path.abspath(venv_path)

    if recreate and os.path.exists(venv_path):
        print(f"Recreating virtual environment at [bold blue]{venv_path}[/bold blue]")
        shutil.rmtree(venv_path)

    venv_bin_python = os.path.join(venv_path, "bin", "python")
    if os.path.exists(venv_path) and not os.path.exists(venv_bin_python):
        print(f"[bold red]Virtual environment at {venv_path} does not exist or is not valid.[/bold red]")
        raise SystemExit()

    if not os.path.exists(venv_path):
        venv.create(venv_path, with_pip=True)
        print(f"Virtual environment created at [bold blue]{venv_path}[/bold blue]")

    return venv_path


def is_airflow_installed(venv_path: str) -> bool:
    venv_bin_python = os.path.join(venv_path, "bin", "python")
    if not os.path.exists(venv_bin_python):
        return False

    try:
        subprocess.run([venv_bin_python, "-m", "airflow", "version"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def install_airflow(
    version: str,
    venv_path: str,
    constraints_url: str,
    extras: str = "",
    requirements: str = "",
    verbose: bool = False,
):
    if is_airflow_installed(venv_path):
        print(
            f"[bold yellow]Apache Airflow {version} is already installed. Skipping installation.[/bold yellow]"
        )
        return

    venv_bin_python = os.path.join(venv_path, "bin", "python")
    if not os.path.exists(venv_bin_python):
        print(f"[bold red]Virtual environment at {venv_path} does not exist or is not valid.[/bold red]")
        raise SystemExit()

    upgrade_pipeline_command = f"{venv_bin_python} -m pip install --upgrade pip setuptools wheel"

    install_command = f"{upgrade_pipeline_command} && {venv_bin_python} -m pip install 'apache-airflow=={version}{extras}' --constraint {constraints_url}"

    if requirements:
        install_command += f" -r {requirements}"

    try:
        if verbose:
            print(f"Running command: [bold]{install_command}[/bold]")
        subprocess.run(install_command, shell=True, check=True)
        print(f"[bold green]Apache Airflow {version} installed successfully![/bold green]")
        print(f"Virtual environment at {venv_path}")
    except subprocess.CalledProcessError:
        print("[bold red]Error occurred during installation.[/bold red]")
        raise SystemExit()


def _get_conf_or_raise(key: str, settings: dict) -> str:
    if key not in settings:
        typer.echo(f"Key '{key}' not found in settings file.")
        raise typer.Exit(1)
    return settings[key]


@app.command()
def build(
    project_path: Path = typer.Argument(Path.cwd(), help="Absolute path to the Airflow project directory."),
    settings_file: Path = typer.Option(
        Path.cwd() / SETTINGS_FILENAME,
        help="Path to the settings file.",
    ),
    venv_path: Path = typer.Option(
        Path.cwd() / ".venv",
        help="Path to the virtual environment.",
    ),
    recreate_venv: bool = typer.Option(
        False,
        help="Recreate virtual environment if it already exists.",
    ),
):
    """Build an Airflow project."""
    project_path = Path(project_path).absolute()
    settings_file = Path(settings_file).absolute()

    if not Path(project_path / SETTINGS_FILENAME).exists():
        typer.echo(f"Settings file '{settings_file}' not found.")
        raise typer.Exit(1)

    with open(settings_file) as f:
        config = yaml.safe_load(f)

    airflow_version = _get_conf_or_raise("airflow_version", config)
    python_version = _get_conf_or_raise("python_version", config)
    constraints_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-{airflow_version}/constraints-{python_version}.txt"

    # Create virtual environment
    venv_path = verify_or_create_venv(venv_path, recreate_venv)

    # Install Airflow and dependencies
    install_airflow(
        version=airflow_version,
        venv_path=venv_path,
        constraints_url=constraints_url,
    )

    typer.echo("Airflow project built successfully.")
    return venv_path


def source_env_file(env_file: str | Path):
    try:
        load_dotenv(env_file)
    except Exception as e:
        typer.echo(f"Error loading .env file: {e}")
        raise typer.Exit(1)


def activate_virtualenv_cmd(venv_path: str | Path) -> str:
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


def terminate_process_tree(pid):
    try:
        process = psutil.Process(pid)
        for child in process.children(recursive=True):
            child.terminate()
        process.terminate()
    except psutil.NoSuchProcess:
        pass


@app.command()
def start(
    project_path: Path = typer.Argument(Path.cwd(), help="Absolute path to the Airflow project directory."),
    venv_path: Path = typer.Option(
        Path.cwd() / ".venv",
        help="Path to the virtual environment.",
    ),
    background: bool = typer.Option(
        False,
        help="Run Airflow in the background.",
    ),
):
    """Start Airflow."""
    env_file = Path(project_path) / ".env"

    if not Path(venv_path).exists():
        # If the virtual environment does not exist, show a prompt to build the project
        # and confirm and run the build command
        typer.echo("Project has not been built yet.")
        if not typer.confirm("Do you want to build the project now?"):
            raise typer.Exit(1)
        typer.echo("Building project...")
        build(
            project_path=project_path, settings_file=Path(project_path) / "settings.yaml", venv_path=venv_path
        )

    if not env_file.exists():
        typer.echo(".env file not found.")
        raise typer.Exit(1)

    # Source the .env file to set environment variables
    source_env_file(env_file)
    os.environ["AIRFLOW_HOME"] = str(project_path)

    venv_path = Path(venv_path).absolute()
    activate_cmd = activate_virtualenv_cmd(venv_path)

    try:
        # Activate the virtual environment and then run the airflow command
        if not background:
            subprocess.run(f"{activate_cmd} && airflow standalone", shell=True, check=True, env=os.environ)
            return

        process = subprocess.Popen(f"{activate_cmd} && airflow standalone", shell=True, env=os.environ)
        process_id = process.pid
        print(f"Airflow is starting in the background (PID: {process_id}).")

        # Persist the process ID to a file
        with open(f"{project_path}/.airflowctl/.background_process_ids", "w") as f:
            f.write(str(process_id))

    except subprocess.CalledProcessError as e:
        typer.echo(f"Error starting Airflow: {e}")
        raise typer.Exit(1)


@app.command()
def stop(
    project_path: Path = typer.Argument(default=Path.cwd(), help="Path to the Airflow project directory."),
):
    """Stop a running background Airflow process and its entire process tree."""
    process_id_file = Path(project_path) / ".airflowctl" / ".background_process_ids"

    if not process_id_file.exists():
        typer.echo("No background processes found.")
        raise typer.Exit(1)

    with open(process_id_file) as f:
        process_ids = f.readlines()

    process_ids = [int(pid.strip()) for pid in process_ids if pid.strip()]

    if not process_ids:
        typer.echo("No background processes found.")
        raise typer.Exit(1)

    try:
        for pid in process_ids:
            terminate_process_tree(pid)
        print("All background processes and their entire process trees have been stopped.")
    except Exception as e:
        typer.echo(f"Error stopping background processes: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
