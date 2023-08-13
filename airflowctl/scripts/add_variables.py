import sys
from pathlib import Path

import yaml
from airflow.exceptions import AirflowException
from rich import print


def variables_import(variables: list):
    """Import variables from a dict."""
    from airflow.models.variable import Variable

    variables = variables or []

    suc_count = fail_count = 0
    for variable in variables:
        if "serialize_json" not in variable:
            variable["serialize_json"] = not isinstance(variable.get("value", ""), str)
        try:
            Variable.set(**variable)
        except Exception as e:
            print(f"Variable import failed: {repr(e)}")
            fail_count += 1
        else:
            suc_count += 1
    print(f"{suc_count} of {len(variables)} variables successfully updated.")
    if fail_count:
        print(f"{fail_count} variable(s) failed to be updated.")
        raise SystemExit("Variable import failed.")


# Import variables defined in settings.yaml file
settings_file = sys.argv[1]
settings_file_path = Path(settings_file)
if not settings_file_path.exists():
    raise AirflowException(f"Settings file not found: {settings_file_path}")

with open(settings_file_path) as f:
    settings = yaml.safe_load(f)

variables = settings.get("variables", []) or []
variables_import(variables)
