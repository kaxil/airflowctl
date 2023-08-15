from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer
import yaml
from rich import print

from airflowctl.utils.project import get_settings_file_path_or_raise, is_astro_project


def add_connections(project_path: Path, activate_cmd: str):
    settings_yaml = get_settings_file_path_or_raise(project_path=project_path)

    with open(settings_yaml) as f:
        settings = yaml.safe_load(f)

    connections = settings.get("connections", []) or []

    if is_astro_project(project_path):
        connections = settings.get("airflow", {}).get("connections", []) or []

    if not connections:
        return

    # Check add_connections script exists
    conn_script_path = f"{Path(__file__).parent.parent.absolute()}/scripts/add_connections.py"
    if not Path(conn_script_path).exists():
        typer.echo(f"Script {conn_script_path} not found.")
        raise typer.Exit(1)

    print("Adding connections...")
    cmd_to_add_connections = f"python {conn_script_path} {settings_yaml}"
    subprocess.run(f"{activate_cmd} && {cmd_to_add_connections}", shell=True, check=True, env=os.environ)
