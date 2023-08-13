# airflowctl

`airflowctl` is a command-line tool for managing Airflow projects. It provides commands to build, initialize, and start Apache Airflow projects.

## Installation

```bash
pip install airflowctl
```

## Quickstart

To initialize a new Airflow project with the latest airflow version, build a venv and run:

```shell
airflowctl init my_airflow_project --build-start
```

## Usage

Initialize a new Airflow project:

```shell
airflowctl init my_airflow_project --airflow-version 2.6.3
```

Build and start an Airflow project:

```shell
airflowctl init my_airflow_project --airflow-version 2.6.3 --python-version 3.8 --build-start
```

Build an existing Airflow project:

```shell
airflowctl build my_airflow_project
```

Start an Airflow project:

```shell
airflowctl start my_airflow_project
```

To get help on a specific command, run:

```shell
airflowctl <command> --help
```
