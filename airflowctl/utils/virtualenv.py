from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import print


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


def source_env_file(env_file: str | Path):
    try:
        load_dotenv(env_file)
    except Exception as e:
        typer.echo(f"Error loading .env file: {e}")
        raise typer.Exit(1)


INSTALLED_PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
