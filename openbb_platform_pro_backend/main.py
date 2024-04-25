"""Generate and serve the widgets.json from the OpenBB Platform API."""

import json

from fastapi.responses import JSONResponse
from openbb_core.api.rest_api import app

from .utils import (
    get_data_schema_for_widget,
    get_query_schema_for_widget,
    data_schema_to_columns_defs,
)


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
                "index": "date",
            },
        },
    }

    if columns_defs:
        widget_config["data"]["table"]["columnsDefs"] = columns_defs

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


def launch_api():
    """Main function."""
    import uvicorn  # pylint: disable=import-outside-toplevel

    uvicorn.run("openbb_platform_pro_backend.main:app", reload=True)


if __name__ == "__main__":
    launch_api()
