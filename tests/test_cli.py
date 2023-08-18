from typer.testing import CliRunner

from airflowctl.cli import app

runner = CliRunner()


def test_init_command(tmpdir):
    tmpdir = str(tmpdir)
    result = runner.invoke(
        app,
        [
            "init",
            tmpdir,
            "--project-name",
            "my_project",
            "--airflow-version",
            "2.6.3",
            "--build-start",
            "--background",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Airflow project built successfully." in result.output


def test_build_command(tmpdir):
    tmpdir = str(tmpdir)
    result = runner.invoke(
        app,
        [
            "init",
            tmpdir,
            "--project-name",
            "my_project",
        ],
    )

    assert result.exit_code == 0, result.output
    result_1 = runner.invoke(
        app,
        [
            "build",
            tmpdir,
        ],
    )

    assert result_1.exit_code == 0, result_1.output
    assert "Airflow project built successfully." in result_1.output

    result_2 = runner.invoke(app, ["info", tmpdir])
    output_2 = result_2.output
    assert result_1.exit_code == 0, output_2
    assert "Airflow Project Information" in output_2
    assert "Airflow Version: " in output_2
    assert "Project Path:" in output_2
    assert "Python Version: " in output_2

    result_3 = runner.invoke(app, ["list"])
    output_3 = result_3.output
    assert result_3.exit_code == 0, output_3
    assert "Project Name" in output_3
    assert "Project Path" in output_3
    assert "Airflow Version" in output_3
