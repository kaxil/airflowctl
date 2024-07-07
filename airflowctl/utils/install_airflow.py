from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx
from rich import print


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


def is_airflow_installed(venv_path: str, airflow_version, project_path: Path) -> bool:
    venv_bin_airflow = os.path.join(venv_path, "bin", "airflow")
    if not os.path.exists(venv_bin_airflow):
        return False

    try:
        completed_process = subprocess.run([venv_bin_airflow, "version"], stdout=subprocess.PIPE, text=True)
        installed_version = completed_process.stdout.strip()
        if installed_version == airflow_version:
            return True
        else:
            print(
                f"[bold yellow]Apache Airflow {installed_version} is installed. "
                f"Apache Airflow {airflow_version} is required.[/bold yellow]"
            )
            # Remove airflow.db if it exists to prevent conflicts with DB migrations
            airflow_db_path = project_path / "airflow.db"
            if airflow_db_path.exists():
                airflow_db_path.unlink()

            return False
    except subprocess.CalledProcessError:
        return False


def install_airflow(
    version: str,
    venv_path: str,
    python_version: str,
    project_path: Path,
    extras: str = "",
    requirements: bool = True,
    verbose: bool = False,
):
    if is_airflow_installed(venv_path, version, project_path=project_path):
        print(
            f"[bold yellow]Apache Airflow {version} is already installed. Skipping installation.[/bold yellow]"
        )
        return

    venv_bin_python = os.path.join(venv_path, "bin", "python")
    if not os.path.exists(venv_bin_python):
        print(f"[bold red]Virtual environment at {venv_path} does not exist or is not valid.[/bold red]")
        raise SystemExit()

    upgrade_pipeline_command = f"{venv_bin_python} -m pip install --upgrade pip setuptools wheel"

    constraints_url = os.getenv("AIRFLOWCTL_CONSTRAINTS")

    install_command = f"{upgrade_pipeline_command} && {venv_bin_python} -m pip install "

    if requirements:
        install_command += f" -r {os.path.join(project_path, 'requirements.txt')}"

    extra_pip_flags = os.getenv("AIRFLOWCTL_PIP_FLAGS")
    if extra_pip_flags:
        install_command += f" {extra_pip_flags}"

    # Check if version is a local path
    is_local_path = Path(version).exists()

    if is_local_path:
        install_command = f"{install_command} . "
    else:
        install_command = f"{install_command} 'apache-airflow=={version}{extras}' "
        constraints_url = constraints_url or (
            f"https://raw.githubusercontent.com/apache/airflow/"
            f"constraints-{version}/constraints-{_get_major_minor_version(python_version)}.txt"
        )

    if constraints_url and not os.getenv("AIRFLOWCTL_SKIP_CONSTRAINTS"):
        install_command += f" --constraint {constraints_url} "

    try:
        if verbose:
            print(f"Running command: [bold]{install_command}[/bold]")
        if is_local_path:
            subprocess.run(install_command, shell=True, check=True, cwd=version)
        else:
            subprocess.run(install_command, shell=True, check=True)
        print(f"[bold green]Apache Airflow {version} installed successfully![/bold green]")
        print(f"Virtual environment at {venv_path}")
    except subprocess.CalledProcessError:
        print("[bold red]Error occurred during installation.[/bold red]")
        raise SystemExit()


def _get_major_minor_version(python_version: str) -> str:
    major, minor = map(int, python_version.split(".")[:2])
    return f"{major}.{minor}"
