import tempfile

import pytest
from typer.testing import CliRunner

from airflowctl.cli import app

runner = CliRunner()


@pytest.fixture(scope="function")
def temp_project_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_init_command(temp_project_dir):
    result = runner.invoke(
        app,
        [
            "init",
            temp_project_dir,
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


def test_build_command(temp_project_dir):
    result = runner.invoke(
        app,
        [
            "init",
            temp_project_dir,
            "--project-name",
            "my_project",
        ],
    )

    assert result.exit_code == 0, result.output
    result_1 = runner.invoke(
        app,
        [
            "build",
            temp_project_dir,
            # "--recreate-venv"
        ],
    )

    assert result_1.exit_code == 0, result_1.output
    assert "Airflow project built successfully." in result_1.output
