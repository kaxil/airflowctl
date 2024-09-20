from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer
import yaml
from rich import print

from airflowctl.modes.virtualenv import VirtualenvMode
from airflowctl.utils.install_airflow import install_airflow
from airflowctl.utils.project import INSTALLED_PYTHON_VERSION, get_settings_file_path_or_raise


class UvMode(VirtualenvMode):
    def build(self, recreate_venv: bool = False):
        venv_path = str(self.venv_path)

        if not self.airflow_version:
            settings_file = get_settings_file_path_or_raise(self.project_path)
            with settings_file.open() as f:
                settings = yaml.safe_load(f)
            self.airflow_version = settings.get("airflow_version")

        if not self.python_version:
            settings_file = get_settings_file_path_or_raise(self.project_path)
            with settings_file.open() as f:
                settings = yaml.safe_load(f)
            self.python_version = settings.get("python_version", INSTALLED_PYTHON_VERSION)

        # Create virtual environment
        venv_path = self.verify_or_create_venv(
            venv_path=venv_path,
            recreate=recreate_venv,
            python_version=self.python_version,
        )

        # Install Airflow and dependencies
        install_airflow(
            version=self.airflow_version,
            venv_path=str(venv_path),
            python_version=self.python_version,
            project_path=self.project_path,
            pip_provider="uv pip",
        )

        # add venv_path to config.yaml
        project_config_yaml = self.project_path / ".airflowctl" / "config.yaml"
        with project_config_yaml.open() as f:
            project_config = yaml.safe_load(f) or {}
        project_config["venv_path"] = str(venv_path)
        with project_config_yaml.open("w") as f:
            yaml.dump(project_config, f)

        return venv_path

    @classmethod
    def verify_or_create_venv(cls, venv_path: str | Path, recreate: bool, python_version: str):
        if isinstance(venv_path, str):
            venv_path = Path(venv_path).absolute()

        if recreate and os.path.exists(venv_path):
            print(f"Recreating virtual environment at [bold blue]{venv_path}[/bold blue]")
            shutil.rmtree(venv_path)

        venv_bin_python = os.path.join(venv_path, "bin", "python")
        if os.path.exists(venv_path) and not os.path.exists(venv_bin_python):
            print(f"[bold red]Virtual environment at {venv_path} does not exist or is not valid.[/bold red]")
            raise SystemExit()

        cls.create_virtualenv_with_specific_python_version(venv_path, python_version)
        return venv_path

    @classmethod
    def create_virtualenv_with_specific_python_version(cls, venv_path: Path, python_version: str):
        if isinstance(venv_path, str):
            venv_path = Path(venv_path)
        venv_path = str(venv_path.absolute())

        # Check if uv is available
        if shutil.which("uv"):
            # Use pyenv to install and set the desired Python version
            print("pyenv found. Using uv to install and set the desired Python version.")
        else:
            print("Install uv to use a specific Python version.")
            raise typer.Exit(code=1)

        # Create the virtual environment
        subprocess.run(
            ["uv", "venv", venv_path, "--python", python_version],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )

        venv_bin_python = os.path.join(venv_path, "bin", "python")

        # Continue with using the virtual environment
        subprocess.run([venv_bin_python, "-m", "ensurepip"], check=True)
        subprocess.run([venv_bin_python, "-m", "pip", "install", "--upgrade", "pip", "uv"], check=True)
        print(
            f"Virtual environment created at [bold blue]{venv_path}[/bold blue] with Python version {python_version}"
        )
