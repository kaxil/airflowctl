from unittest import mock

import pytest
import yaml
from airflow.exceptions import AirflowException
from airflow.models.variable import Variable

from airflowctl.scripts.add_variables import extract_variable_from_settings, variables_import


@pytest.mark.parametrize(
    "settings, expected_result",
    [
        (
            {"variables": [{"variable_name": "var1", "variable_value": "value1"}]},
            [{"variable_name": "var1", "variable_value": "value1"}],
        ),
        (
            {"variables": [{"key": "var1", "value": "value1"}]},
            [{"key": "var1", "value": "value1"}],
        ),
        (
            {"airflow": {"variables": [{"variable_name": "var1", "variable_value": "value1"}]}},
            [{"variable_name": "var1", "variable_value": "value1"}],
        ),
    ],
)
def test_extract_variable_from_settings_success(tmp_path, settings, expected_result):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(yaml.dump(settings))

    result = extract_variable_from_settings(settings_file_path=settings_file)

    assert result == expected_result


def test_extract_variable_from_settings_missing_file(tmp_path):
    settings_file = tmp_path / "settings.yaml"

    with pytest.raises(AirflowException, match="Settings file not found"):
        extract_variable_from_settings(settings_file_path=settings_file)


@pytest.mark.parametrize(
    "variables, expected_set_calls",
    [
        (
            [
                {"variable_name": "var1", "variable_value": "value1"},
                {"variable_name": "var2", "variable_value": "value2"},
            ],
            [
                mock.call(key="var1", value="value1", serialize_json=False),
                mock.call(key="var2", value="value2", serialize_json=False),
            ],
        ),
        (
            [
                {"key": "var1", "value": "val", "description": "description1", "serialize_json": True},
            ],
            [
                mock.call(key="var1", value="val", description="description1", serialize_json=True),
            ],
        ),
        (
            [
                {"key": "var1", "value": 1, "description": "description1"},
            ],
            [
                mock.call(key="var1", value=1, description="description1", serialize_json=True),
            ],
        ),
    ],
)
def test_variables_import_success(tmp_path, variables, expected_set_calls):
    settings = {"variables": variables}
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(yaml.dump(settings))

    with mock.patch.object(Variable, "set") as set_mock:
        with mock.patch("airflowctl.scripts.add_variables.print") as rich_print_mock:
            variables_import(settings_file_path=settings_file)

    set_mock.assert_has_calls(expected_set_calls)
    num_vars = len(variables)
    rich_print_mock.assert_has_calls([mock.call(f"{num_vars} of {num_vars} variables successfully updated.")])


def test_variables_import_failure(tmp_path):
    variables = [
        {"variable_name": "var1", "variable_value": "value1"},
        {"variable_name": "var2", "variable_value": "value2"},
    ]
    settings = {"variables": variables}
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(yaml.dump(settings))

    with mock.patch.object(Variable, "set", side_effect=Exception("Mocked error")):
        with pytest.raises(SystemExit):
            with mock.patch("airflowctl.scripts.add_variables.print") as rich_print_mock:
                variables_import(settings_file_path=settings_file)

    rich_print_mock.assert_has_calls(
        [
            mock.call("Variable import failed: Exception('Mocked error')"),
            mock.call("Variable import failed: Exception('Mocked error')"),
            mock.call("0 of 2 variables successfully updated."),
            mock.call("2 variable(s) failed to be updated."),
        ]
    )


def test_variables_import_no_variables(tmp_path):
    settings = {}
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(yaml.dump(settings))

    with mock.patch.object(Variable, "set") as set_mock:
        with mock.patch("airflowctl.scripts.add_variables.print") as rich_print_mock:
            variables_import(settings_file_path=settings_file)

    assert set_mock.mock.call_count == 0
    rich_print_mock.assert_has_calls([mock.call("0 of 0 variables successfully updated.")])


def test_variables_import_no_settings_file(tmp_path):
    with pytest.raises(AirflowException, match="Settings file not found"):
        variables_import(settings_file_path=tmp_path / "nonexistent.yaml")
