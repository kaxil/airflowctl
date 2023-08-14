# airflowctl

[![PyPI](https://img.shields.io/pypi/v/airflowctl)](https://pypi.org/project/airflowctl/)
[![License](https://img.shields.io/:license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0.txt)
[![Python](https://img.shields.io/pypi/pyversions/airflowctl.svg)](https://pypi.python.org/pypi/airflowctl)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/airflowctl)](https://pypi.org/project/airflowctl/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`airflowctl` is a command-line tool for managing Apache Airflow™ projects.
It provides a set of commands to initialize, build, start, stop, and manage Airflow projects.
With `airflowctl`, you can easily set up and manage your Airflow projects, install
specific versions of Apache Airflow, and manage virtual environments.

The main goal of `airflowctl` is for first-time Airflow users to install and setup Airflow using a single command and
for existing Airflow users to manage multiple Airflow projects with different Airflow versions on the same machine.

## Features

- **Project Initialization with Connections & Variables:** Initialize a new Airflow project with customizable project name, Apache Airflow
version, and Python version. It also allows you to manage Airflow connections and variables.
- **Automatic Virtual Environment Management:** Automatically create and manage virtual environments for
your Airflow projects, even for Python versions that are not installed on your system.
- **Airflow Version Management:** Install and manage specific versions of Apache Airflow.
- **Background Process Management:** Start and stop Airflow in the background with process management capabilities.
- **Live Logs Display:** Continuously display live logs of background Airflow processes with optional log filtering.

## Table of Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
  - [Step 1: Initialize a New Project](#step-1-initialize-a-new-project)
  - [Step 2: Build the Project](#step-2-build-the-project)
  - [Step 3: Start Airflow](#step-3-start-airflow)
  - [Step 4: Monitor Logs](#step-4-monitor-logs)
  - [Step 5: Stop Airflow](#step-5-stop-airflow)
  - [Step 6: List Airflow Projects](#step-6-list-airflow-projects)
  - [Step 7: Show Project Info & Using Airflow commands](#step-7-show-project-info--using-airflow-commands)


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

### Step 1: Initialize a New Project

To create a new Apache Airflow project, use the init command.
This command sets up the basic project structure, including configuration files,
directories, and sample DAGs.


```shell
airflowctl init <project_name> --airflow-version <version> --python-version <version>
```

Example:

```shell
airflowctl init my_airflow_project --airflow-version 2.6.3 --python-version 3.8
```

This creates a new project directory with the following structure:

```shell
my_airflow_project
├── .env
├── .gitignore
├── dags
│   └── example_dag_basic.py
├── plugins
├── requirements.txt
└── settings.yaml
```

Description of the files and directories:
- `.env` file contains the environment variables for the project.
- `.gitignore` file contains the default gitignore settings.
- `dags` directory contains the sample DAGs.
- `plugins` directory contains the sample plugins.
- `requirements.txt` file contains the project dependencies.
- `settings.yaml` file contains the project settings, including the project name,
Airflow version, Python version, and virtual environment path.

In our example `settings.yaml` file would look like this:

```yaml
# Airflow version to be installed
airflow_version: "2.6.3"

# Python version for the project
python_version: "3.8"

# Airflow connections
connections:
    # Example connection
    # - conn_id: example
    #   conn_type: http
    #   host: http://example.com
    #   port: 80
    #   login: user
    #   password: pass
    #   schema: http
    #   extra:
    #      example_extra_field: example-value

# Airflow variables
variables:
    # Example variable
    # - key: example
    #   value: example-value
    #   description: example-description
```

Edit the `settings.yaml` file to customize the project settings.

### Step 2: Build the Project

The build command creates the virtual environment, installs the specified Apache Airflow
version, and sets up the project dependencies.

Run the build command from the project directory:

```shell
cd my_airflow_project
airflowctl build
```

The CLI relies on [`pyenv`](https://github.com/pyenv/pyenv) to download and install a Python version if the version is not already installed.

Example, if you have Python 3.8 installed but you specify Python 3.7 in the `settings.yaml` file,
the CLI will install Python 3.7 using `pyenv` and create a virtual environment with Python 3.7 first.

### Step 3: Start Airflow

To start Airflow services, use the start command.
This command activates the virtual environment and launches the Airflow web server and scheduler.

Example:

```shell
airflowctl start my_airflow_project
```

You can also start Airflow in the background with the `--background` flag:

```shell
airflowctl start my_airflow_project --background
```

### Step 4: Monitor Logs

To monitor logs from the background Airflow processes, use the logs command.
This command displays live logs and provides options to filter logs for specific components.

Example
```shell
airflowctl logs my_airflow_project
```

To filter logs for specific components:

```shell
# Filter logs for scheduler
airflowctl logs my_airflow_project -s

# Filter logs for webserver
airflowctl logs my_airflow_project -w

# Filter logs for triggerer
airflowctl logs my_airflow_project -t

# Filter logs for scheduler and webserver
airflowctl logs my_airflow_project -s -w
```

### Step 5: Stop Airflow

To stop Airflow services if they are still running, use the stop command.

Example:

```shell
airflowctl stop my_airflow_project
```

### Step 6: List Airflow Projects

To list all Airflow projects, use the list command.

Example:

```shell
airflowctl list
```

### Step 7: Show Project Info & Using Airflow commands

To show project info, use the info command.

Example:

```shell
# From the project directory
airflowctl info

# From outside the project directory
airflowctl info my_airflow_project
```

To run Airflow commands, activate the virtual environment first and then run the commands.

Example:

```shell
# From the project directory
source .venv/bin/activate

# Source all the environment variables
source .env
airflow version
```

To add a new DAG, add the DAG file to the `dags` directory.

To edit an existing DAG, edit the DAG file in the `dags` directory.
The changes will be reflected in the Airflow web server.

### Other Commands

For more information and options, you can use the `--help` flag with each command.

## License

This project is licensed under the terms of the [Apache 2.0 License](LICENSE)
