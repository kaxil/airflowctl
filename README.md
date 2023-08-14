# airflowctl

`airflowctl` is a command-line tool for managing Apache Airflow projects.
It provides a set of commands to initialize, build, start, stop, and manage Airflow projects.
With airflowctl, you can easily set up and manage your Airflow projects, install
specific versions of Apache Airflow, and manage virtual environments.

## Features

- **Project Initialization:** Initialize a new Airflow project with customizable project name, Apache Airflow version, and Python version.
- **Automatic Virtual Environment Management:** Automatically create and manage virtual environments for your Airflow projects.
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

For more information and options, you can use the `--help` flag with each command.
