from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv
from packaging import version
from rich import print
from rich.console import Console

from airflowctl.utils.connections import add_connections
from airflowctl.utils.install_airflow import install_airflow
from airflowctl.utils.paths import convert_str_or_path_to_absolute_path
from airflowctl.utils.project import INSTALLED_PYTHON_VERSION, get_settings_file_path_or_raise
from airflowctl.utils.variables import add_variables


class VirtualenvMode:
    def __init__(
        self,
        project_path: Path,  # TODO: Make this current working directory by default
        python_version: str | None = None,
        airflow_version: str | None = None,
        venv_path: str | None = None,
    ):
        self.project_path = convert_str_or_path_to_absolute_path(project_path)

        self.airflow_version = airflow_version
        self.python_version = python_version
        # TODO: Make this just a Path object
        if not venv_path:
            settings_file = get_settings_file_path_or_raise(self.project_path, raise_if_not_found=False)
            if settings_file.exists():
                with settings_file.open() as f:
                    settings = yaml.safe_load(f)
                venv_path = settings.get("mode", {}).get("virtualenv", {}).get("venv_path")

        self.venv_path: Path = convert_str_or_path_to_absolute_path(venv_path) or self.project_path / ".venv"
        self.env_file: Path = self.project_path / ".env"

        self.background_process_ids_file: Path = self.project_path / ".airflowctl" / ".background_process_ids"
        self.background_logs_info_file: Path = self.project_path / "background_logs_info.txt"

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
        venv_path = verify_or_create_venv(
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
        )

        # add venv_path to config.yaml
        project_config_yaml = self.project_path / ".airflowctl" / "config.yaml"
        with project_config_yaml.open() as f:
            project_config = yaml.safe_load(f) or {}
        project_config["venv_path"] = str(venv_path)
        with project_config_yaml.open("w") as f:
            yaml.dump(project_config, f)

        return venv_path

    def has_built(self) -> bool:
        return self.venv_path.exists()

    def start(self, background: bool = False):
        project_path = self.project_path

        if not self.env_file.exists():
            typer.echo(".env file not found.")
            raise typer.Exit(1)

        self._setup_env_vars_to_run_airflow()

        activate_cmd = activate_virtualenv_cmd(self.venv_path)

        try:
            # Verify that Airflow is installed and get the version
            print("Verifying Airflow installation...")
            subprocess.run(
                f"{activate_cmd} && airflow db upgrade && airflow version",
                shell=True,
                check=True,
                env=os.environ,
            )

            # Add connections
            add_connections(project_path, activate_cmd)

            # Add variables
            add_variables(project_path, activate_cmd)

            # Activate the virtual environment and then run the airflow command
            if not background:
                subprocess.run(
                    f"{activate_cmd} && airflow standalone", shell=True, check=True, env=os.environ
                )
                return

            if not self.background_process_ids_file.exists():
                self.background_process_ids_file.parent.mkdir(parents=True, exist_ok=True)
                self.background_process_ids_file.touch()

            bg_process_file = str(self.background_process_ids_file.resolve())

            # Create a temporary file to capture the logs
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
                # Save the temporary file name to a known location
                self.background_logs_info_file.write_text(temp_file.name)

                # Activate the virtual environment and then run the airflow command in the background
                subprocess.Popen(
                    f"{activate_cmd} && airflow standalone > {temp_file.name} 2>&1 & echo $! > {bg_process_file}",
                    shell=True,
                    env=os.environ,
                )

                # Wait for a bit to ensure the subprocesses are started
                time.sleep(5)

                # Read the background process PID
                with open(bg_process_file) as f:
                    bg_process_pid = int(f.read())

                print(f"Airflow is starting in the background (PID: {bg_process_pid}).")
                print("Logs are being captured. You can use 'airflowctl logs' to view the logs.")

        except subprocess.CalledProcessError as e:
            typer.echo(f"Error starting Airflow: {e}")
            raise typer.Exit(1)

    def logs(self, webserver: bool = False, scheduler: bool = False, triggerer: bool = False):
        if not self.background_logs_info_file.exists():
            typer.echo("No background logs found.")
            raise typer.Exit(1)

        temp_file_name = self.background_logs_info_file.read_text().strip()
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

    def stop(self):
        if not self.background_process_ids_file.exists():
            typer.echo("No background processes found.")
            raise typer.Exit(1)

        with open(self.background_process_ids_file) as f:
            process_ids = f.readlines()

        process_ids = [int(pid.strip()) for pid in process_ids if pid.strip()]

        if not process_ids:
            typer.echo("No background processes found.")
            raise typer.Exit(1)

        try:
            for pid in process_ids:
                self._terminate_process_tree(pid)
            print(
                f"All background processes ({process_ids}) and their entire process trees have been stopped."
            )
        except Exception as e:
            typer.echo(f"Error stopping background processes: {e}")
            raise typer.Exit(1)

    def run_airflow_command(self, command: str):
        self._setup_env_vars_to_run_airflow()
        activate_cmd = activate_virtualenv_cmd(self.venv_path)

        try:
            subprocess.run(f"{activate_cmd} && airflow {command}", shell=True, check=True, env=os.environ)
        except subprocess.CalledProcessError as e:
            typer.echo(f"Error running Airflow command: {e}")
            raise typer.Exit(1)

    def print_info(self, console: Console, project_config: dict | None = None):
        venv_path = Path(project_config.get("venv_path", self.venv_path))
        venv_path = venv_path.absolute() if venv_path.exists() else "N/A"

        settings_file = get_settings_file_path_or_raise(project_path=self.project_path)
        with open(settings_file) as f:
            settings = yaml.safe_load(f) or {}

        python_version = settings.get("python_version", "N/A")
        airflow_version = settings.get("airflow_version", "N/A")

        console.print(f"Python Version: {python_version}")
        console.print(f"Airflow Version: {airflow_version}")
        console.print(f"Environment file: {self.env_file}")
        console.print(f"Virtual environment path: {venv_path}")
        console.print(f"Background process IDs file: {self.background_process_ids_file}")
        console.print(f"Background logs info file: {self.background_logs_info_file}")
        console.print(f"Airflow binary: {self.venv_path}/bin/airflow")
        console.print(f"Python: {self.venv_path}/bin/python")

        print("\n")
        self.print_next_steps(venv_path=self.venv_path, airflow_version=airflow_version)
        print()

    def print_next_steps(self, venv_path: Path, airflow_version: str):
        activated_venv_path = os.environ.get("VIRTUAL_ENV")

        next_steps = "Next Steps:"
        activate_command = activate_virtualenv_cmd(venv_path)

        assert (
            venv_path.exists()
        ), f"Virtual environment does not exist: {venv_path}. Run 'airflowctl build' to create it."

        need_to_activate = not activated_venv_path or activated_venv_path != os.path.dirname(venv_path)
        if need_to_activate:
            next_steps += f"""
        # Activate the virtual environment:
            [bold blue]{activate_command}[/bold blue]
        """

        if (
            os.environ.get("AIRFLOW_HOME") != str(self.project_path)
            and self.env_file.exists()
            and "AIRFLOW_HOME" not in self.env_file.read_text()
        ):
            next_steps += f"""
        # Set AIRFLOW_HOME to the project path:
            [bold blue]$ export AIRFLOW_HOME={self.project_path}[/bold blue]
        """

        next_steps += f"""
        # Source the environment variables:
            [bold blue]$ source .env[/bold blue]

        # You can now run all the  "airflow" commands in your terminal. For example:
            [bold blue]$ airflow version[/bold blue]

        # Run Apache Airflow in standalone mode using the following command:
            [bold blue]$ airflow standalone[/bold blue]

        # Access the Airflow UI in your web browser at: [bold cyan]http://localhost:8080[/bold cyan]

        # For more information and guidance, please refer to the Apache Airflow documentation:
        # [bold cyan]https://airflow.apache.org/docs/apache-airflow/{airflow_version}/[/bold cyan]
        """

        print(next_steps)

    @staticmethod
    def _terminate_process_tree(pid):
        import psutil

        try:
            process = psutil.Process(pid)
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()
            process.wait(timeout=10)  # Wait for the main process to finish
        except psutil.NoSuchProcess:
            pass

    def _setup_env_vars_to_run_airflow(self):
        # Source the .env file to set environment variables
        source_env_file(self.env_file)
        os.environ["AIRFLOW_HOME"] = str(self.project_path)

        # Run LocalExecutor for Airflow 2.6
        if not self.airflow_version:
            settings_file = get_settings_file_path_or_raise(self.project_path)
            with settings_file.open() as f:
                settings = yaml.safe_load(f)
            self.airflow_version = settings.get("airflow_version")

            # if self.airflow_version is a file or a directory, then it is a path to Airflow source code
            if Path(self.airflow_version).exists():
                try:
                    output = subprocess.run(
                        f"{self.venv_path}/bin/airflow version 2>/dev/null",
                        shell=True,
                        check=True,
                        env=os.environ,
                        capture_output=True,
                        text=True,
                    )
                    self.airflow_version = output.stdout
                except subprocess.CalledProcessError:
                    pass

        if (
            self.airflow_version
            and is_valid_pep440_version(self.airflow_version)
            and version.parse(self.airflow_version) >= version.parse("2.6.0")
        ):
            os.environ["AIRFLOW__CORE__EXECUTOR"] = "LocalExecutor"
            os.environ["_AIRFLOW__SKIP_DATABASE_EXECUTOR_COMPATIBILITY_CHECK"] = "1"


def is_valid_pep440_version(version_str: str) -> bool:
    try:
        version.parse(version_str)
        return True
    except version.InvalidVersion:
        return False


def create_virtualenv_with_specific_python_version(venv_path: Path, python_version: str):
    if isinstance(venv_path, str):
        venv_path = Path(venv_path)
    venv_path = str(venv_path.absolute())

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
    subprocess.run([py_venv_bin_python, "-m", "venv", venv_path, "--clear"], check=True)

    venv_bin_python = os.path.join(venv_path, "bin", "python")

    # Continue with using the virtual environment
    subprocess.run([venv_bin_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    print(
        f"Virtual environment created at [bold blue]{venv_path}[/bold blue] with Python version {python_version}"
    )


def verify_or_create_venv(venv_path: str | Path, recreate: bool, python_version: str):
    if isinstance(venv_path, str):
        venv_path = Path(venv_path).absolute()

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


def activate_virtualenv_cmd(venv_path: Path | str) -> str:
    if isinstance(venv_path, str):
        venv_path = Path(venv_path)
    venv_path = str(venv_path.resolve())
    if os.name == "posix":
        bin_path = os.path.join(venv_path, "bin", "activate")
        activate_cmd = f". {bin_path}"
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
