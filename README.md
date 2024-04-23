# OpenBB Platform backend for OpenBB Terminal Pro

The application in this repository wraps the OpenBB Platform API in a way tha it:

1. Creates a widgets.json from the OpenAPI schema
2. Creates the widgets.json and root ("/) endpoints

## Installation and running

Install this repository using pip (or clone and install with poetry):

```bash
pip install https://github.com/OpenBB-finance/openbb-platform-pro-backend
```

The package provides a shortcut to launch the application using:

```bash
openbb-platform-pro-backend
```

:Note: If this command is not available, you may need to deactivate and activate back your virtual environment.
