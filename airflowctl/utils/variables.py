from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer
import yaml
from rich import print

from airflowctl.utils.project import get_settings_file_path_or_raise, is_astro_project


def add_variables(project_path: Path, activate_cmd: str):
    settings_yaml = get_settings_file_path_or_raise(project_path=project_path)

    with open(settings_yaml) as f:
        settings = yaml.safe_load(f)

    variables = settings.get("variables", []) or []

    if is_astro_project(project_path):
        variables = settings.get("airflow", {}).get("variables", []) or []

    if not variables:
        return

    # Check add_variables script exists
    var_script_path = f"{Path(__file__).parent.parent.absolute()}/scripts/add_variables.py"
    if not Path(var_script_path).exists():
        typer.echo(f"Script {var_script_path} not found.")
        raise typer.Exit(1)

    print("Adding variables...")
    cmd_to_add_variables = f"python {var_script_path} {settings_yaml}"
    subprocess.run(f"{activate_cmd} && {cmd_to_add_variables}", shell=True, check=True, env=os.environ)
