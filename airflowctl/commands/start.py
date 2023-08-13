import os
import subprocess
import typer
import yaml
from dotenv import load_dotenv

app = typer.Typer()

def source_env_file(env_file: str):
    try:
        load_dotenv(env_file)
    except Exception as e:
        typer.echo(f"Error loading .env file: {e}")
        raise typer.Exit(1)

def activate_virtualenv(venv_path: str):
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

@app.command()
def start(
    project_path: str = typer.Argument(..., help="Absolute path to the Airflow project directory."),
):
    config_file = os.path.join(project_path, "config.yaml")
    env_file = os.path.join(project_path, ".env")

    if not os.path.exists(config_file):
        typer.echo(f"Config file '{config_file}' not found.")
        raise typer.Exit(1)

    if not os.path.exists(env_file):
        typer.echo(f".env file not found.")
        raise typer.Exit(1)

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # Source the .env file to set environment variables
    source_env_file(env_file)
    os.environ["AIRFLOW_HOME"] = project_path
    os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = "sqlite:///" + os.path.abspath(os.path.join(project_path, "airflow.db"))
    venv_path = os.path.abspath(config.get("venv_path", os.path.join(project_path, ".venv/airflow")))
    activate_cmd = activate_virtualenv(venv_path)

    try:
        # Activate the virtual environment and then run the airflow command
        subprocess.run(f"{activate_cmd} && airflow standalone", shell=True, check=True, env=os.environ)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error starting Airflow: {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
