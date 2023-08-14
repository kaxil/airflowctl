from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import httpx
import psutil
import typer
import yaml
from dotenv import load_dotenv
from rich import print
from rich.console import Console

app = typer.Typer()

SETTINGS_FILENAME = "settings.yaml"
INSTALLED_PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


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
    if not settings_file.exists():
        file_contents = f"""
# Airflow version to be installed
airflow_version: "{airflow_version}"

# Python version for the project
python_version: "{python_version}"

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
        default=INSTALLED_PYTHON_VERSION,
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


def create_virtualenv_with_specific_python_version(venv_path: Path, python_version: str):
    # Check if pyenv is available
    if shutil.which("pyenv"):
        # Use pyenv to install and set the desired Python version
        print("pyenv found. Using pyenv to install and set the desired Python version.")
        subprocess.run(["pyenv", "install", python_version, "--skip-existing"], check=True)
    else:
        print("Install pyenv to use a specific Python version.")
        raise typer.Exit(code=1)

    result = subprocess.run(
        ["pyenv", "prefix", python_version], stdout=subprocess.PIPE, text=True, check=True
    )
    python_ver_path = result.stdout.strip()

    py_venv_bin_python = os.path.join(python_ver_path, "bin", "python")

    # Create the virtual environment using venv
    subprocess.run([py_venv_bin_python, "-m", "venv", venv_path], check=True)

    venv_bin_python = os.path.join(venv_path, "bin", "python")

    # Continue with using the virtual environment
    subprocess.run([venv_bin_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    print(
        f"Virtual environment created at [bold blue]{venv_path}[/bold blue] with Python version {python_version}"
    )


def verify_or_create_venv(venv_path: str | Path, recreate: bool, python_version: str):
    venv_path = os.path.abspath(venv_path)

    if recreate and os.path.exists(venv_path):
        print(f"Recreating virtual environment at [bold blue]{venv_path}[/bold blue]")
        shutil.rmtree(venv_path)

    venv_bin_python = os.path.join(venv_path, "bin", "python")
    if os.path.exists(venv_path) and not os.path.exists(venv_bin_python):
        print(f"[bold red]Virtual environment at {venv_path} does not exist or is not valid.[/bold red]")
        raise SystemExit()

    if python_version != INSTALLED_PYTHON_VERSION:
        print(
            f"Python version ({python_version}) is different from the default Python version ({sys.version})."
        )
        create_virtualenv_with_specific_python_version(venv_path, python_version)

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


def _get_major_minor_version(python_version: str) -> str:
    major, minor = map(int, python_version.split(".")[:2])
    return f"{major}.{minor}"


def airflowctl_project_check(project_path: str | Path):
    """Check if the current directory is an Airflow project."""
    # Abort if .airflowctl directory does not exist in the project
    airflowctl_dir = Path(project_path) / ".airflowctl"
    if not airflowctl_dir.exists():
        print("Not an airflowctl project. Run 'airflowctl init' to initialize the project.")
        raise typer.Exit(1)


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
    """
    Build an Airflow project. This command sets up the project environment, installs Apache Airflow
    and its dependencies.
    """

    airflowctl_project_check(project_path)
    project_path = Path(project_path).absolute()
    settings_file = Path(settings_file).absolute()

    if not Path(project_path / SETTINGS_FILENAME).exists():
        typer.echo(f"Settings file '{settings_file}' not found.")
        raise typer.Exit(1)

    with open(settings_file) as f:
        config = yaml.safe_load(f)

    airflow_version = _get_conf_or_raise("airflow_version", config)
    python_version = _get_major_minor_version(_get_conf_or_raise("python_version", config))

    constraints_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-{airflow_version}/constraints-{python_version}.txt"

    # Create virtual environment
    venv_path = verify_or_create_venv(venv_path, recreate_venv, python_version)

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


def add_connections(project_path: Path, activate_cmd: str):
    # Check settings file exists
    settings_yaml = Path(f"{project_path}/settings.yaml")
    if not settings_yaml.exists():
        typer.echo(f"Settings file {settings_yaml} not found.")
        raise typer.Exit(1)

    with open(settings_yaml) as f:
        settings = yaml.safe_load(f)

    connections = settings.get("connections", []) or []
    if not connections:
        return

    # Check add_connections script exists
    conn_script_path = f"{Path(__file__).parent.absolute()}/scripts/add_connections.py"
    if not Path(conn_script_path).exists():
        typer.echo(f"Script {conn_script_path} not found.")
        raise typer.Exit(1)

    print("Adding connections...")
    cmd_to_add_connections = f"python {conn_script_path} {settings_yaml}"
    subprocess.run(f"{activate_cmd} && {cmd_to_add_connections}", shell=True, check=True, env=os.environ)


def add_variables(project_path: Path, activate_cmd: str):
    # Check settings file exists
    settings_yaml = Path(f"{project_path}/settings.yaml")
    if not settings_yaml.exists():
        typer.echo(f"Settings file {settings_yaml} not found.")
        raise typer.Exit(1)

    with open(settings_yaml) as f:
        settings = yaml.safe_load(f)

    variables = settings.get("variables", []) or []
    if not variables:
        return

    # Check add_variables script exists
    var_script_path = f"{Path(__file__).parent.absolute()}/scripts/add_variables.py"
    if not Path(var_script_path).exists():
        typer.echo(f"Script {var_script_path} not found.")
        raise typer.Exit(1)

    print("Adding variables...")
    cmd_to_add_variables = f"python {var_script_path} {settings_yaml}"
    subprocess.run(f"{activate_cmd} && {cmd_to_add_variables}", shell=True, check=True, env=os.environ)


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
    airflowctl_project_check(project_path)

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
        # Verify that Airflow is installed and get the version
        print("Verifying Airflow installation...")
        subprocess.run(f"{activate_cmd} && airflow version", shell=True, check=True, env=os.environ)

        # Add connections
        add_connections(project_path, activate_cmd)

        # Add variables
        add_variables(project_path, activate_cmd)

        # Activate the virtual environment and then run the airflow command
        if not background:
            subprocess.run(f"{activate_cmd} && airflow standalone", shell=True, check=True, env=os.environ)
            return

        # Create a temporary file to capture the logs
        with tempfile.NamedTemporaryFile(mode="w+") as temp_file:
            # Save the temporary file name to a known location
            logs_info_file = Path(project_path) / "background_logs_info.txt"
            logs_info_file.write_text(temp_file.name)

            # Activate the virtual environment and then run the airflow command in the background
            process = subprocess.Popen(
                f"{activate_cmd} && airflow standalone > {temp_file.name} 2>&1 &", shell=True, env=os.environ
            )

            process_id = process.pid
            print(f"Airflow is starting in the background (PID: {process_id}).")
            print("Logs are being captured. You can use 'airflowctl logs' to view the logs.")

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
    airflowctl_project_check(project_path)
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


@app.command()
def logs(
    project_path: str = typer.Argument(Path.cwd(), help="Absolute path to the Airflow project directory."),
    webserver: bool = typer.Option(
        False,
        "-w",
        help="Filter logs for the Webserver",
    ),
    scheduler: bool = typer.Option(
        False,
        "-s",
        help="Filter logs for the Scheduler",
    ),
    triggerer: bool = typer.Option(
        False,
        "-t",
        help="Filter logs for the Triggerer",
    ),
):
    """Continuously display live logs of the background Airflow processes."""

    airflowctl_project_check(project_path)

    logs_info_file = Path(project_path) / "background_logs_info.txt"

    if not logs_info_file.exists():
        print("Background logs information file not found.")
        return

    temp_file_name = logs_info_file.read_text().strip()

    try:
        console = Console()

        with open(temp_file_name) as temp_file:
            console.print("Displaying live background logs... (Press Ctrl+C to stop)", style="bold")

            try:
                # Use the `tail` command to continuously display logs from the temp file
                tail_process = subprocess.Popen(["tail", "-f", temp_file.name], stdout=subprocess.PIPE)

                while True:
                    line = tail_process.stdout.readline().decode("utf-8")
                    if not line:
                        break

                    # Check for component-specific logs
                    is_webserver_log = webserver and "webserver" in line.lower()
                    is_scheduler_log = scheduler and "scheduler" in line.lower()
                    is_triggerer_log = triggerer and "triggerer" in line.lower()

                    # Remove ANSI color codes using regular expressions
                    line = re.sub(r"\x1B\[[0-9;]*[mK]", "", line)

                    if is_webserver_log or is_scheduler_log or is_triggerer_log:
                        # Display logs in different colors based on the component
                        if is_webserver_log:
                            console.print(line, style="bold cyan")
                        elif is_scheduler_log:
                            console.print(line, style="bold magenta")
                        elif is_triggerer_log:
                            console.print(line, style="bold yellow")
                    elif not (webserver or scheduler or triggerer):
                        console.print(line)
            except KeyboardInterrupt:
                print("\nLogs display stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
