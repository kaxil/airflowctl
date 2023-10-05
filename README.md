# airflowctl

[![PyPI](https://img.shields.io/pypi/v/airflowctl)](https://pypi.org/project/airflowctl/)
[![License](https://img.shields.io/:license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0.txt)
[![Python](https://img.shields.io/pypi/pyversions/airflowctl.svg)](https://pypi.python.org/pypi/airflowctl)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/airflowctl)](https://pypi.org/project/airflowctl/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/kaxil/airflowctl/main.svg)](https://results.pre-commit.ci/latest/github/kaxil/airflowctl/main)

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
  - [Step 7: Show Project Info](#step-7-show-project-info)
  - [Step 8: Running Airflow Commands](#step-8-running-airflow-commands)
  - [Step 9: Changing Airflow configuration](#step-9-changing-airflow-configurations)
- [Using with other Airflow tools](#using-with-other-airflow-tools)
  - [Astro CLI](#astro-cli)

## Installation

```bash
pip install airflowctl
```

## Quickstart

To initialize a new Airflow project with the latest airflow version, build a Virtual environment
and run the project, run the following command:

```shell
airflowctl init my_airflow_project --build-start
```

This will start Airflow and display the logs in the terminal. You can
access the Airflow UI at http://localhost:8080. To stop Airflow, press `Ctrl+C`.

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


# Path to a virtual environment to be used for the project
mode:
  virtualenv:
    venv_path: "PROJECT_DIR/.venv"

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

Optionally, you can choose custom virtual environment path in case you have already installed apache-airflow package
and other dependencies.
Pass the existing virtualenv path using `--venv_path` option to the `init` command or in `settings.yaml` file.
Make sure the existing virtualenv has same airflow and python version as your `settings.yaml` file states.

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

### Step 7: Show Project Info

To show project info, use the info command.

Example:

```shell
# From the project directory
airflowctl info

# From outside the project directory
airflowctl info my_airflow_project
```

### Step 8: Running Airflow commands

To run Airflow commands, use the `airflowctl airflow` command. All the commands after
`airflowctl airflow` are passed to the Airflow CLI.:

```shell
# From the project directory
airflowctl airflow <airflow_command>
```

Example:

```shell
$ airflowctl airflow version
2.6.3
```

You can also run `airflowctl airflow --help` to see the list of available commands.

```shell
$ airflowctl airflow --help
Usage: airflowctl airflow [OPTIONS] COMMAND [ARGS]...

  Run Airflow commands.

Positional Arguments:
  GROUP_OR_COMMAND

    Groups:
      celery         Celery components
      config         View configuration
      connections    Manage connections
      dags           Manage DAGs
      db             Database operations
      jobs           Manage jobs
      kubernetes     Tools to help run the KubernetesExecutor
      pools          Manage pools
      providers      Display providers
      roles          Manage roles
      tasks          Manage tasks
      users          Manage users
      variables      Manage variables

    Commands:
      cheat-sheet    Display cheat sheet
      dag-processor  Start a standalone Dag Processor instance
      info           Show information about current Airflow and environment
      kerberos       Start a kerberos ticket renewer
      plugins        Dump information about loaded plugins
      rotate-fernet-key
                     Rotate encrypted connection credentials and variables
      scheduler      Start a scheduler instance
      standalone     Run an all-in-one copy of Airflow
      sync-perm      Update permissions for existing roles and optionally DAGs
      triggerer      Start a triggerer instance
      version        Show the version
      webserver      Start a Airflow webserver instance

Options:
  -h, --help         show this help message and exit
```

Example:

```shell
# Listing dags
$ airflowctl airflow dags list
dag_id            | filepath             | owner   | paused
==================+======================+=========+=======
example_dag_basic | example_dag_basic.py | airflow | True


# Running standalone
$ airflowctl airflow standalone
```

Or you can activate the virtual environment first and then run the commands as shown below.

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

### Step 9: Changing Airflow Configurations

`airflowctl` by default uses SQLite as the backend database and `SequentialExecutor` as the executor.
However, if you want to use other databases or executors, you can stop the project and
either a) edit the `airflow.cfg` file or b) add environment variables to the `.env` file.

Example:

```shell
# Stop the project
airflowctl stop my_airflow_project

# Changing the executor to LocalExecutor
# Change the database to PostgreSQL if you already have it installed
echo "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@localhost:5432/airflow" >> .env
echo "AIRFLOW__CORE__EXECUTOR=LocalExecutor" >> .env

# Start the project

airflowctl start my_airflow_project
```

Check the [Airflow documentation](https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html)
for all the available Airflow configurations.

#### Using Local Executor with SQLite
For Airflow >= 2.6, you can run `LocalExecutor` with `sqlite` as the backend database by
adding the following environment variable to the `.env` file:

```shell
_AIRFLOW__SKIP_DATABASE_EXECUTOR_COMPATIBILITY_CHECK=1
AIRFLOW__CORE__EXECUTOR=LocalExecutor
```

This should automatically happen for you when you run `airflowctl airflow` command if
Airflow version `==2.6.*`.

> [!WARNING]
> Sqlite is not recommended for production use. Use it only for development and testing only.

### Other Commands

For more information and options, you can use the `--help` flag with each command.

## Using with other Airflow tools

`airflowctl` can be used with other Airflow projects as long as the project structure is the same.

### Astro CLI

`airflowctl` can be used with [Astro CLI](https://github.com/astronomer/astro-cli) projects too.

While `airflowctl` is a tool that allows you to run Airflow locally using virtual environments, Astro CLI
allows you to run Airflow locally using docker.

`airflowctl` can read the `airflow_settings.yaml` file generated by Astro CLI for reading connections & variables. It
will then reuse it as `settings` file for `airflowctl`.

For example, if you have an Astro CLI project:
- Run the `airflowctl init . --build-start` command to initialize `airflowctl` from the project directory.
Press `y` to continue when prompted.
- It will then ask you for the Airflow version, enter the version you are using, by
default uses the latest Airflow version, press enter to continue
- It will use the installed Python version as the project's python version. If you
want to use a different Python version, you can specify it in the `airflow_settings.yaml` file in the
`python_version` field.

```shell
# From the project directory
$ cd astro_project
$ airflowctl init . --build-start
Directory /Users/xyz/astro_project is not empty. Continue? [y/N]: y
Project /Users/xyz/astro_project added to tracking.
Airflow project initialized in /Users/xyz/astro_project
Detected Astro project. Using Astro settings file (/Users/kaxilnaik/Desktop/proj1/astro_project/airflow_settings.yaml).
'airflow_version' not found in airflow_settings.yaml file. What is the Airflow version? [2.6.3]:
Virtual environment created at /Users/xyz/astro_project/.venv
...
...
```

If you see an error like the following, remove `airflow.cfg` file from the project directory and remove
`AIRFLOW_HOME` from `.env` file if it exists and try again.

```shell
Error: there might be a problem with your project starting up.
The webserver health check timed out after 1m0s but your project will continue trying to start.
Run 'astro dev logs --webserver | --scheduler' for details.
```

## License

This project is licensed under the terms of the [Apache 2.0 License](LICENSE)
