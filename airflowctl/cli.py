from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import psutil
import typer
import yaml
from rich import print
from rich.console import Console
from rich.table import Table

from airflowctl.utils.connections import add_connections
from airflowctl.utils.install_airflow import get_latest_airflow_version, install_airflow
from airflowctl.utils.project import (
    GLOBAL_TRACKING_FILE,
    SETTINGS_FILENAME,
    airflowctl_project_check,
    create_project,
    get_conf_or_raise,
    get_settings_file_path_or_raise,
)
from airflowctl.utils.variables import add_variables
from airflowctl.utils.virtualenv import (
    INSTALLED_PYTHON_VERSION,
    activate_virtualenv_cmd,
    source_env_file,
    verify_or_create_venv,
)

app = typer.Typer()


@app.command()
def init(
    project_path: Path = typer.Argument(
        ...,
        help="Path to initialize the project in.",
    ),
    project_name: str = typer.Option(
        default="",
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
    project_dir, settings_file = create_project(project_name, project_path, airflow_version, python_version)
    if build_start:
        venv_path = Path(project_dir / ".venv")
        build(project_path=project_dir, settings_file=settings_file, venv_path=venv_path, recreate_venv=False)
        start(project_path=project_dir, venv_path=venv_path, background=background)


@app.command()
def build(
    project_path: Path = typer.Argument(Path.cwd(), help="Absolute path to the Airflow project directory."),
    settings_file: Path = typer.Option(
        None, help="Path to the settings file. Defaults to PROJECT_DIR/settings.yaml.", show_default=False
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

    settings_file = get_settings_file_path_or_raise(project_path, settings_file)

    with open(settings_file) as f:
        config = yaml.safe_load(f)

    airflow_version = get_conf_or_raise("airflow_version", config)
    python_version = get_conf_or_raise("python_version", config)

    # Create virtual environment
    venv_path = verify_or_create_venv(venv_path, recreate_venv, python_version)

    # Install Airflow and dependencies
    install_airflow(
        version=airflow_version,
        venv_path=venv_path,
        python_version=python_version,
    )

    # add venv_path to config.yaml
    project_config_yaml = project_path / ".airflowctl" / "config.yaml"
    with project_config_yaml.open() as f:
        project_config = yaml.safe_load(f) or {}
    project_config["venv_path"] = str(venv_path)
    with project_config_yaml.open("w") as f:
        yaml.dump(project_config, f)

    typer.echo("Airflow project built successfully.")
    return venv_path


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
            project_path=project_path,
            settings_file=Path(project_path) / SETTINGS_FILENAME,
            venv_path=venv_path,
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
        subprocess.run(
            f"{activate_cmd} && airflow db upgrade && airflow version", shell=True, check=True, env=os.environ
        )

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


@app.command("list")
def list_cmd():
    """List all Airflow projects created using this CLI."""

    tracking_file = GLOBAL_TRACKING_FILE

    if not tracking_file.exists():
        print("No tracked Airflow projects found.")
        return

    with open(tracking_file) as f:
        contents = yaml.safe_load(f)

    tracked_projects = contents.get("projects", [])

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project Name", style="dim")
    table.add_column("Project Path")
    table.add_column("Python Version")
    table.add_column("Airflow Version")

    for project_dir in tracked_projects:
        settings_file = Path(project_dir) / "settings.yaml"

        if not settings_file.exists():
            continue

        with open(settings_file) as sf:
            settings = yaml.safe_load(sf)

        with open(Path(project_dir) / ".airflowctl" / "config.yaml") as cf:
            project_config = yaml.safe_load(cf)

        project_name = project_config.get("project_name", "N/A")
        python_version = settings.get("python_version", "N/A")
        airflow_version = settings.get("airflow_version", "N/A")

        table.add_row(
            project_name,
            project_dir,
            python_version,
            airflow_version,
        )

    console = Console()
    console.print(table)


@app.command()
def info(
    project_path: Path = typer.Argument(Path.cwd(), help="Absolute path to the Airflow project directory."),
):
    """Display information about the current Airflow project."""

    airflowctl_project_check(project_path)

    project_path = Path(project_path)
    settings_file = project_path / SETTINGS_FILENAME
    project_conf_path = Path(project_path) / ".airflowctl" / "config.yaml"

    project_config = yaml.safe_load(project_conf_path.read_text())
    project_name = project_config.get("project_name", "N/A")
    venv_path = Path(project_config.get("venv_path")) or (Path(project_path) / ".venv")
    venv_path = venv_path.absolute() if venv_path.exists() else "N/A"

    if not settings_file.exists():
        typer.echo(f"Settings file '{settings_file}' not found.")
        raise typer.Exit(1)

    with open(settings_file) as f:
        settings = yaml.safe_load(f)

    python_version = settings.get("python_version", "N/A")
    airflow_version = settings.get("airflow_version", "N/A")

    console = Console()
    console.print("Airflow Project Information", style="bold cyan")
    console.print(f"Project Name: {project_name}")
    console.print(f"Project Path: {project_path.absolute()}")
    console.print(f"Python Version: {python_version}")
    console.print(f"Airflow Version: {airflow_version}")
    console.print(f"Virtual Environment: {venv_path}")
    console.print(f"Python: {venv_path}/bin/python")
    console.print(f"Airflow binary: {venv_path}/bin/airflow")

    print("\n")
    print_next_steps(venv_path, airflow_version)
    print()


def print_next_steps(venv_path: str | Path, version: str):
    activated_venv_path = os.environ.get("VIRTUAL_ENV")

    next_steps = "Next Steps:"

    activate_command = activate_virtualenv_cmd(venv_path)

    assert Path(venv_path).exists()

    need_to_activate = not activated_venv_path or activated_venv_path != os.path.dirname(venv_path)
    if need_to_activate:
        next_steps += f"""
    * Activate the virtual environment:
        [bold blue]{activate_command}[/bold blue]

    * Source the environment variables:
        [bold blue]$ source .env[/bold blue]
    """

    next_steps += f"""
    * You can now run all the  "airflow" commands in your terminal. For example:
        [bold blue]$ airflow version[/bold blue]

    * Run Apache Airflow in standalone mode using the following command:
        [bold blue]$ airflow standalone[/bold blue]

    * Access the Airflow UI in your web browser at: [bold cyan]http://localhost:8080[/bold cyan]

    For more information and guidance, please refer to the Apache Airflow documentation:
    [bold cyan]https://airflow.apache.org/docs/apache-airflow/{version}/[/bold cyan]
    """

    print(next_steps)


if __name__ == "__main__":
    app()
