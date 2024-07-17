# OpenBB Platform backend for OpenBB Terminal Pro

The application in this repository wraps the OpenBB Platform API in a way that it:

1. Creates a widgets.json from the OpenAPI schema
2. Creates the widgets.json and root ("/") endpoints for the OpenBB Platform API

## Installation

Install from pypi _into the same python environment as your OpenBB Platform_:

```bash
pip install openbb-platform-pro-backend
```

## Running

The package provides a shortcut to launch the application using:

```bash
openbb-api
```

**:note:** If this command is not available immediately after installation, you need to deactivate and activate back your virtual environment.

**:note:** Set up your provider API keys in the `~/.openbb_platform/user_settings.json` file.

## Configuring host and port

You can configure the host and port by setting the `OPENBB_API_HOST` and `OPENBB_API_PORT` environment variables.
