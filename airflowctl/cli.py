from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich import print
from rich.console import Console
from rich.table import Table

from airflowctl.modes.virtualenv import VirtualenvMode
from airflowctl.utils.install_airflow import get_latest_airflow_version
from airflowctl.utils.project import (
    GLOBAL_TRACKING_FILE,
    INSTALLED_PYTHON_VERSION,
    airflowctl_project_check,
    create_project,
    get_conf_or_raise,
    get_settings_file_path_or_raise,
)

app = typer.Typer()

# TODO: Add a --verbose flag to all commands
# TODO: Add a --project-path flag to all commands

project_path_argument = typer.Argument(
    Path.cwd(),
    help="Absolute path to the Airflow project directory.",
    exists=True,
    file_okay=False,
    resolve_path=True,
)


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
    venv_path: Path = typer.Option(
        None,
        help="Path to the venv directory. Defaults to PROJECT_DIR/.venv/",
    ),
):
    """
    Initialize a new Airflow project.
    """
    project_dir, settings_file = create_project(
        project_name, project_path, airflow_version, python_version, venv_path
    )
    if build_start:
        build(project_path=project_dir, settings_file=settings_file, recreate_venv=False)
        start(project_path=project_dir, background=background)


@app.command()
def build(
    project_path: Path = project_path_argument,
    settings_file: Path = typer.Option(
        None, help="Path to the settings file. Defaults to PROJECT_DIR/settings.yaml.", show_default=False
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
    venv_path = config.get("venv_path", None)

    mode = VirtualenvMode(project_path, python_version, airflow_version, venv_path)
    venv_path = mode.build(recreate_venv=recreate_venv)

    typer.echo("Airflow project built successfully.")
    return venv_path


@app.command()
def start(
    project_path: Path = project_path_argument,
    background: bool = typer.Option(
        False,
        help="Run Airflow in the background.",
    ),
):
    """Start Airflow."""
    airflowctl_project_check(project_path)

    mode = VirtualenvMode(project_path)
    if not mode.has_built():
        # Build the project if it has not been built yet
        print("Project has not been built yet.")
        if not typer.confirm("Do you want to build the project now?"):
            raise typer.Exit(1)
        print("Building project...")
        mode.build()
    mode.start(background=background)


@app.command()
def stop(project_path: Path = project_path_argument):
    """Stop a running background Airflow process and its entire process tree."""
    airflowctl_project_check(project_path)
    mode = VirtualenvMode(project_path)
    mode.stop()


@app.command()
def logs(
    project_path: Path = project_path_argument,
    webserver: bool = typer.Option(False, "-w", help="Filter logs for the Webserver"),
    scheduler: bool = typer.Option(False, "-s", help="Filter logs for the Scheduler"),
    triggerer: bool = typer.Option(False, "-t", help="Filter logs for the Triggerer"),
):
    """Continuously display live logs of the background Airflow processes."""

    airflowctl_project_check(project_path)
    mode = VirtualenvMode(project_path=project_path)
    mode.logs(webserver=webserver, scheduler=scheduler, triggerer=triggerer)


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
        settings_file = get_settings_file_path_or_raise(
            project_path=Path(project_dir),
            raise_if_not_found=False,
            verbose=False,
        )

        if not settings_file.exists():
            continue

        with open(settings_file) as sf:
            settings = yaml.safe_load(sf)

        config_file = Path(project_dir) / ".airflowctl" / "config.yaml"
        if not config_file.exists():
            continue

        with open(config_file) as cf:
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
def info(project_path: Path = project_path_argument):
    """Display information about the current Airflow project."""

    airflowctl_project_check(project_path)

    project_path = Path(project_path)
    project_conf_path = Path(project_path) / ".airflowctl" / "config.yaml"

    project_config = yaml.safe_load(project_conf_path.read_text())
    project_name = project_config.get("project_name", "N/A")

    console = Console()
    console.print("Airflow Project Information", style="bold cyan")
    console.print(f"Project Name: {project_name}")
    console.print(f"Project Path: {project_path.absolute()}")

    mode = VirtualenvMode(project_path=project_path)
    mode.print_info(project_config=project_config, console=console)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def airflow(
    ctx: typer.Context,
    project_path: Path = typer.Option(
        Path.cwd(),
        help="Absolute path to the Airflow project directory.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
):
    """Forward commands to Airflow CLI."""
    airflowctl_project_check(project_path)

    command = " ".join(ctx.args)

    mode = VirtualenvMode(project_path)
    mode.run_airflow_command(command)


@app.callback()
def main(ctx: typer.Context):
    """Streamline getting started with Apache Airflow™ and managing multiple Airflow projects."""

    # If the subcommand is 'airflow', we don't want to show the "airflowctl "help option
    # and instead want to show the "airflow" help option
    if ctx.invoked_subcommand == "airflow":
        ctx.help_option_names = []


if __name__ == "__main__":
    app()
