import pytest
from airflow.models.connection import Connection

from airflowctl.scripts.add_connections import _create_connection


@pytest.mark.parametrize(
    "value, expected_connection",
    [
        ("url_value", Connection(conn_id="test_conn", uri="url_value")),
        (
            {"conn_id": "test_conn", "conn_type": "http", "conn_host": "example.com"},
            Connection(conn_id="test_conn", conn_type="http", host="example.com"),
        ),
        # Add more test cases as needed
    ],
)
def test_create_connection(value, expected_connection):
    conn = _create_connection("test_conn", value)
    assert conn.get_uri() == expected_connection.get_uri()
