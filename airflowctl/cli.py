import typer

from airflowctl.commands import init, build, start, list

app = typer.Typer()

app.add_typer(init.app, name="init")
app.add_typer(build.app, name="build")
app.add_typer(start.app, name="start")
app.add_typer(list.app, name="list")

if __name__ == "__main__":
    app()
