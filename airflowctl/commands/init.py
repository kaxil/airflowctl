import os
import yaml
from pathlib import Path
import typer

app = typer.Typer()

CONFIG_FILENAME = "config.yaml"


def create_project(config_path: str):
    # Create the project directory structure
    os.makedirs(config_path, exist_ok=True)
    dags_dir = os.path.join(config_path, "dags")
    os.makedirs(dags_dir, exist_ok=True)

    airflow_version = "2.6.0"
    python_version = "3.10"
    constraints_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-{airflow_version}/constraints-{python_version}.txt"
    # Initialize the config file
    config_file = os.path.join(config_path, CONFIG_FILENAME)
    if not os.path.exists(config_file):
        default_config = {
            "python_version": python_version,
            "airflow_version": airflow_version,
            "constraints_url": "",
            "environment_variables": {},
            "variables": {},
            "connections": {},
        }
        with open(config_file, "w") as f:
            yaml.dump(default_config, f)

    typer.echo(f"Airflow project initialized in {config_path}")


@app.command()
def init(
    config_path: str = typer.Option(
        ".",
        help="Path where the Airflow project will be initialized.",
    )
):
    """
    Initialize a new Airflow project.
    """
    create_project(config_path)


if __name__ == "__main__":
    app()
