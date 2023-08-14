from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer
import yaml
from rich import print


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
