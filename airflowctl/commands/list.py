import os
import typer
import yaml

app = typer.Typer()

PROJECTS_DB_FILE = os.path.expanduser("~/.airflowctl_projects.yaml")


def load_projects():
    if os.path.exists(PROJECTS_DB_FILE):
        with open(PROJECTS_DB_FILE, "r") as f:
            projects = yaml.safe_load(f)
            return projects
    return {}


@app.command()
def list():
    projects = load_projects()

    if not projects:
        typer.echo("No projects found.")
        return

    typer.echo("List of projects:")
    for name, path in projects.items():
        typer.echo(f"{name}: {path}")


if __name__ == "__main__":
    app()
