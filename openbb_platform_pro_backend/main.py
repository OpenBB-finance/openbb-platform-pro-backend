"""Generate and serve the widgets.json for the OpenBB Platform API."""

import json
import os
import socket
from pathlib import Path
from fastapi.responses import JSONResponse
from openbb_core.api.rest_api import app

from .utils import (
    get_data_schema_for_widget,
    get_query_schema_for_widget,
    data_schema_to_columns_defs,
)

CURRENT_USER_SETTINGS = os.environ.get("HOME") + "/.openbb_platform/user_settings.json"
USER_SETTINGS_COPY = CURRENT_USER_SETTINGS.replace("user_settings.json", "user_settings_copy.json")


def check_port(host, port) -> int:
    """Check if the port number is free."""
    not_free = True
    port = int(port) - 1
    while not_free:
        port = port + 1
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            res = sock.connect_ex((host, port))
            if res != 0:
                not_free = False
    return port


openapi = app.openapi()
widgets_json = {}

routes = [
    p for p in openapi["paths"] if p.startswith("/api") and "get" in openapi["paths"][p]
]
for route in routes:
    route_api = openapi["paths"][route]
    widget_id = route_api["get"]["operationId"]

    # Prepare the query schema of the widget
    query_schema, has_chart = get_query_schema_for_widget(openapi, route)

    # Prepare the data schema of the widget
    data_schema = get_data_schema_for_widget(openapi, widget_id)
    if (
        data_schema
        and "properties" in data_schema
        and "results" in data_schema["properties"]
    ):
        response_schema_refs = data_schema["properties"]["results"]
        columns_defs = data_schema_to_columns_defs(openapi, response_schema_refs)

    widget_config = {
        "name": f'OBB {route_api["get"]["operationId"].replace("_", " ").title()}',
        "description": route_api["get"]["description"],
        "category": route_api["get"]["tags"][0].title(),
        "widgetType": route_api["get"]["tags"][0],
        "widgetId": f"OBB {widget_id}",
        "params": query_schema,  # Use the fetched query schema
        "endpoint": route.replace("/api", "api"),
        "gridData": {"w": 20, "h": 5},
        "data": {
            "dataKey": "results",
            "table": {
                "showAll": True,
            },
        },
    }

    if columns_defs:
        widget_config["data"]["table"]["columnsDefs"] = columns_defs
        if "date" in columns_defs:
            widget_config["data"]["table"]["index"] = "date"
        if "period" in columns_defs:
            widget_config["data"]["table"]["index"] = "period"

    # Add the widget configuration to the widgets.json
    widgets_json[widget_config["widgetId"]] = widget_config

    if has_chart:
        # deepcopy the widget_config
        widget_config_chart = json.loads(json.dumps(widget_config))
        del widget_config_chart["data"]["table"]

        widget_config_chart["name"] = f"{widget_config_chart['name']} Chart"
        widget_config_chart["widgetId"] = f"{widget_config_chart['widgetId']}_chart"
        widget_config_chart["params"]["chart"] = True

        widget_config_chart["defaultViz"] = "chart"
        widget_config_chart["data"]["dataKey"] = "chart.content"
        widget_config_chart["data"]["chart"] = {
            "type": "line",
        }

        widgets_json[widget_config_chart["widgetId"]] = widget_config_chart

# Write the widgets_json to a file for debugging purposes
with open("widgets.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(widgets_json, indent=4))


@app.get("/")
async def get_root():
    """API Root."""
    return JSONResponse(content={})


@app.get("/widgets.json")
async def get_widgets():
    """Widgets configuration file for the OpenBB Terminal Pro."""
    return JSONResponse(content=widgets_json)


# pylint: disable=import-outside-toplevel
def launch_api():
    """Main function."""
    import uvicorn

    if Path(CURRENT_USER_SETTINGS).exists():
        with open(CURRENT_USER_SETTINGS, "r") as f:
            current_settings = json.load(f)
    else:
        current_settings = {"credentials": {}, "preferences": {}, "defaults": {"commands": {}}}

    pat = input(
        "\n\nEnter your personal access token (PAT) to authorize the API and update your local settings."
        + "\nSkip to use a pre-configured 'user_settings.json' file."
        + "\nPress Enter to skip or copy your PAT to the command line: "
    )

    if pat:
        from openbb_core.app.service.hub_service import HubService

        try:
            Hub = HubService()
            _ = Hub.connect(pat=pat)
            hub_settings = Hub.pull()
            hub_credentials = json.loads(hub_settings.credentials.model_dump_json())
            hub_preferences = json.loads(hub_settings.preferences.model_dump_json())
            hub_defaults = json.loads(hub_settings.defaults.model_dump_json())
        except Exception as e:
            print(f"\n\nError connecting with Hub:\n{e}")
            hub_credentials = {}
            hub_preferences = {}
            hub_defaults = {}

        # Prompt the user to ask if they want to persist the new settings
        persist_input = input(
            "\n\nDo you want to persist the new settings?"
            + " Not recommended for public machines. (yes/no): "
        ).strip().lower()

        if persist_input in ["yes", "y"]:
            PERSIST = True
        elif persist_input in ["no", "n"]:
            PERSIST = False
        else:
            print("\n\nInvalid input. Defaulting to not persisting the new settings.")
            PERSIST = False

        # Save the current settings to restore at the end of the session.
        if PERSIST is False:
            with open(USER_SETTINGS_COPY, "w") as f:
                json.dump(current_settings, f, indent=4)

        new_settings = current_settings.copy()

        # Update the current settings with the new settings
        if hub_credentials:
            for k, v in hub_credentials.items():
                if v:
                    new_settings["credentials"][k] = v

        if hub_preferences:
            for k, v in hub_credentials.items():
                if v:
                    new_settings["preferences"][k] = v

        if hub_defaults:
            for k, v in hub_defaults.items():
                if k == "commands":
                    for key, value in hub_defaults["commands"].items():
                        if value:
                            new_settings["defaults"]["commands"][key] = value
                elif v:
                    new_settings["defaults"][k] = v
                else:
                    continue
            new_settings["defaults"].update(hub_defaults)

        # Write the new settings to the user_settings.json file
        with open(CURRENT_USER_SETTINGS, "w") as f:
            json.dump(new_settings, f, indent=4)

        current_settings = new_settings

    if current_settings["credentials"].get("OPENAI_API_KEY"):
        print("\n\nOpenAI API Key found, adding to the environment variables.\n")
        os.environ["OPENAI_API_KEY"] = current_settings["credentials"]["OPENAI_API_KEY"]

    host = os.getenv("OPENBB_API_HOST", "127.0.0.1")
    if not host:
        print(
            "\n\nOPENBB_API_HOST is set incorrectly. It should be an IP address or hostname."
        )
        host = input("Enter the host IP address or hostname: ")
        if not host:
            host = "127.0.0.1"

    port = os.getenv("OPENBB_API_PORT", 8000)

    try:
        port = int(port)
    except ValueError:
        print(
            "\n\nOPENBB_API_PORT is set incorrectly. It should be an port number."
        )
        port = input("Enter the port number: ")
        try:
            port = int(port)
        except ValueError:
            print("\n\nInvalid port number. Defaulting to 8000.")
            port = 8000

    free_port = check_port(host, port)

    if free_port != port:
        print(f"\n\nPort {port} is already in use. Using port {free_port}.\n")
        port = free_port

    try:
        uvicorn.run("openbb_platform_pro_backend.main:app", host=host, port=port)
    finally:
        # If user_settings_copy.json exists, then restore the original settings.
        if os.path.exists(USER_SETTINGS_COPY):
            print("\n\nRestoring the original settings.\n")
            os.replace(USER_SETTINGS_COPY, CURRENT_USER_SETTINGS)

if __name__ == "__main__":
    try:
        launch_api()
    except KeyboardInterrupt:
        print("Restoring the original settings.")
