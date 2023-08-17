from __future__ import annotations

import json
import sys
from inspect import signature
from pathlib import Path
from typing import Any

import yaml
from airflow.exceptions import AirflowException
from airflow.models.connection import Connection
from airflow.utils import helpers
from airflow.utils.session import create_session
from rich import print
from sqlalchemy import select


def get_connection_parameter_names() -> set[str]:
    """Returns :class:`airflow.models.connection.Connection` constructor parameters."""
    return {k for k in signature(Connection.__init__).parameters.keys() if k != "self"}


def _create_connection(conn_id: str, value: Any):
    """Creates a connection based on a URL or JSON object."""
    if isinstance(value, str):
        return Connection(conn_id=conn_id, uri=value)
    if isinstance(value, dict):
        connection_parameter_names = get_connection_parameter_names() | {"extra_dejson"}
        # Handle Astro projects
        if "conn_port" in value:
            value["port"] = value.pop("conn_port")
        if "conn_login" in value:
            value["login"] = value.pop("conn_login")
        if "conn_password" in value:
            value["password"] = value.pop("conn_password")
        if "conn_schema" in value:
            value["schema"] = value.pop("conn_schema")
        if "conn_extra" in value:
            value["extra"] = value.pop("conn_extra")
        if "conn_host" in value:
            value["host"] = value.pop("conn_host")

        current_keys = set(value.keys())

        if not current_keys.issubset(connection_parameter_names):
            illegal_keys = current_keys - connection_parameter_names
            illegal_keys_list = ", ".join(illegal_keys)
            raise AirflowException(
                f"The object have illegal keys: {illegal_keys_list}. "
                f"The dictionary can only contain the following keys: {connection_parameter_names}"
            )
        if "extra" in value and "extra_dejson" in value:
            raise AirflowException(
                "The extra and extra_dejson parameters are mutually exclusive. "
                "Please provide only one parameter."
            )
        if "extra_dejson" in value:
            value["extra"] = json.dumps(value["extra_dejson"])
            del value["extra_dejson"]

        if "conn_id" in current_keys and conn_id != value["conn_id"]:
            raise AirflowException(
                f"Mismatch conn_id. "
                f"The dictionary key has the value: {value['conn_id']}. "
                f"The item has the value: {conn_id}."
            )
        value["conn_id"] = conn_id
        return Connection(**value)
    raise AirflowException(
        f"Unexpected value type: {type(value)}. The connection can only be defined using a string or object."
    )


def _import_helper(connections_dict, overwrite: bool) -> None:
    """Load connections from a file and save them to the DB.

    :param overwrite: Whether to skip or overwrite on collision.
    """

    with create_session() as session:
        for conn_id, conn in connections_dict.items():
            try:
                helpers.validate_key(conn_id, max_length=200)
            except Exception as e:
                print(f"Could not import connection. {e}")
                continue

            existing_conn_id = session.scalar(select(Connection.id).where(Connection.conn_id == conn_id))
            if existing_conn_id is not None:
                if not overwrite:
                    print(f"Could not import connection {conn_id}: connection already exists.")
                    continue

                # The conn_ids match, but the PK of the new entry must also be the same as the old
                conn.id = existing_conn_id

            session.merge(conn)
            session.commit()
            print(f"Imported connection {conn_id}")


if __name__ == "__main__":
    # Import connections defined in settings.yaml file
    settings_file = sys.argv[1]
    settings_file_path = Path(settings_file)
    if not settings_file_path.exists():
        raise AirflowException(f"Settings file not found: {settings_file_path}")

    with open(settings_file_path) as f:
        settings = yaml.safe_load(f)

    connections = settings.get("connections", []) or []

    # Handle Astro projects
    if "airflow" in settings:
        connections = settings.get("airflow").get("connections", []) or []

    connections_list = {}
    for conn in connections:
        connection = _create_connection(conn["conn_id"], conn)
        connections_list[conn["conn_id"]] = connection

    _import_helper(connections_list, overwrite=True)
