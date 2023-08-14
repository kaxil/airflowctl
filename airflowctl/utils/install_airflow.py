from __future__ import annotations

import os
import subprocess

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
    python_version: str,
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

    constraints_url = (
        f"https://raw.githubusercontent.com/apache/airflow/"
        f"constraints-{version}/constraints-{_get_major_minor_version(python_version)}.txt"
    )

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


def _get_major_minor_version(python_version: str) -> str:
    major, minor = map(int, python_version.split(".")[:2])
    return f"{major}.{minor}"
