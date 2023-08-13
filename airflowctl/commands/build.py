import os
import subprocess
import venv
import typer
import yaml

app = typer.Typer()


def create_virtual_env(venv_path: str, python_version: str):
    venv.create(venv_path, with_pip=True, prompt="airflowctl")
    venv_bin_python = os.path.join(venv_path, "bin", "python")
    subprocess.run([venv_bin_python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])


def install_airflow(venv_path: str, constraints_url: str):
    venv_bin_python = os.path.join(venv_path, "bin", "python")
    subprocess.run([venv_bin_python, "-m", "pip", "install", "apache-airflow", "--constraint", constraints_url])


def create_env_file(project_path: str):
    env_file_path = os.path.join(project_path, ".env")
    with open(env_file_path, "w") as env_file:
        env_file.write(f"AIRFLOW_HOME={project_path}\n")


@app.command()
def build(
    project_path: str = typer.Argument(..., help="Absolute path to the Airflow project directory."),
):
    project_path = os.path.abspath(project_path)
    config_file = os.path.join(project_path, "config.yaml")

    if not os.path.exists(config_file):
        typer.echo(f"Config file '{config_file}' not found.")
        raise typer.Exit(1)

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)


    airflow_version = config.get("airflow_version")
    python_version = config.get("python_version")
    constraints_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-{airflow_version}/constraints-{python_version}.txt"

    venv_path = os.path.join(project_path, config.get("venv_path", f".venv/airflow_{airflow_version}_py{python_version}"))
    # Create virtual environment
    create_virtual_env(venv_path, python_version)

    # Install Airflow and dependencies
    install_airflow(venv_path, constraints_url)

    # Create .env file with AIRFLOW_HOME set to project directory
    create_env_file(project_path)

    typer.echo("Airflow project built successfully.")


if __name__ == "__main__":
    app()
