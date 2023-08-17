from __future__ import annotations

import sys
from pathlib import Path

import yaml
from airflow.exceptions import AirflowException
from rich import print


def variables_import(settings_file_path: Path):
    """Import variables from a dict."""
    from airflow.models.variable import Variable

    variables = extract_variable_from_settings(settings_file_path=settings_file_path)

    suc_count = fail_count = 0
    for variable in variables:
        if "serialize_json" not in variable:
            variable["serialize_json"] = not isinstance(variable.get("value", ""), str)

        variable_name = variable.pop("key", "") or variable.pop("variable_name", "")
        if not variable_name:
            print("Variable name empty. Skipping.")
            continue
        variable_value = variable.pop("value", "") or variable.pop("variable_value", "")

        try:
            Variable.set(key=variable_name, value=variable_value, **variable)
        except Exception as e:
            print(f"Variable import failed: {repr(e)}")
            fail_count += 1
        else:
            suc_count += 1
    print(f"{suc_count} of {len(variables)} variables successfully updated.")
    if fail_count:
        print(f"{fail_count} variable(s) failed to be updated.")
        raise SystemExit("Variable import failed.")


def extract_variable_from_settings(settings_file_path: Path):
    """Extract variables from settings.yaml file."""
    if not settings_file_path.exists():
        raise AirflowException(f"Settings file not found: {settings_file_path}")

    with open(settings_file_path) as f:
        settings = yaml.safe_load(f)

    variables = settings.get("variables", []) or []

    # Handle Astro projects
    if "airflow" in settings:
        variables = settings.get("airflow").get("variables", []) or []

    return variables


if __name__ == "__main__":
    # Import variables defined in settings.yaml file
    settings_file = sys.argv[1]
    settings_file_path = Path(settings_file)
    variables_import(settings_file_path)
