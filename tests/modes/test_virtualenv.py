import subprocess
from pathlib import Path
from unittest import mock

import pytest
import typer

from airflowctl.modes.virtualenv import (
    activate_virtualenv_cmd,
    create_virtualenv_with_specific_python_version,
    source_env_file,
)


def test_activate_virtualenv_cmd_posix():
    venv_path = "/path/to/venv"
    expected_cmd = f". {venv_path}/bin/activate"

    with mock.patch("os.name", "posix"):
        cmd = activate_virtualenv_cmd(venv_path)

    assert cmd == expected_cmd


def test_activate_virtualenv_cmd_unsupported_os():
    venv_path = "/path/to/venv"

    with mock.patch("os.name", "unsupported_os"):
        with pytest.raises(typer.Exit):
            activate_virtualenv_cmd(venv_path)


def test_source_env_file_success():
    env_file = "/path/to/.env"

    with mock.patch("airflowctl.modes.virtualenv.load_dotenv") as load_dotenv_mock:
        source_env_file(env_file)

    load_dotenv_mock.assert_called_once_with(env_file)


def test_source_env_file_error():
    env_file = "/path/to/.env"
    exception_message = "Mocked exception message"

    with mock.patch("airflowctl.modes.virtualenv.load_dotenv", side_effect=Exception(exception_message)):
        with pytest.raises(typer.Exit):
            source_env_file(env_file)


def test_create_virtualenv_with_specific_python_version_pyenv_available():
    venv_path = Path("/path/to/venv")
    python_version = "3.8"

    with mock.patch("shutil.which", return_value="/path/to/pyenv"), mock.patch(
        "subprocess.run"
    ) as subprocess_run_mock:
        # Mock the result of subprocess.run for pyenv prefix
        subprocess_run_mock.side_effect = [
            subprocess.CompletedProcess(
                ["pyenv", "install", python_version, "--skip-existing"], returncode=0
            ),
            subprocess.CompletedProcess(
                ["pyenv", "prefix", python_version], returncode=0, stdout=f"{venv_path}\n"
            ),
            subprocess.CompletedProcess(
                [str(venv_path / "bin" / "python"), "-m", "venv", str(venv_path)], returncode=0
            ),
            subprocess.CompletedProcess(
                [str(venv_path / "bin" / "python"), "-m", "pip", "install", "--upgrade", "pip"], returncode=0
            ),
        ]

        create_virtualenv_with_specific_python_version(venv_path, python_version)

    expected_calls = [
        mock.call(["pyenv", "install", python_version, "--skip-existing"], check=True),
        mock.call(["pyenv", "prefix", python_version], stdout=subprocess.PIPE, text=True, check=True),
        mock.call([str(venv_path / "bin" / "python"), "-m", "venv", str(venv_path)], check=True),
        mock.call(
            [str(venv_path / "bin" / "python"), "-m", "pip", "install", "--upgrade", "pip"], check=True
        ),
    ]

    subprocess_run_mock.assert_has_calls(expected_calls)


def test_create_virtualenv_with_specific_python_version_pyenv_not_available():
    venv_path = Path("/path/to/venv")
    python_version = "3.8"

    with mock.patch("shutil.which", return_value=None):
        with pytest.raises(typer.Exit):
            create_virtualenv_with_specific_python_version(venv_path, python_version)
