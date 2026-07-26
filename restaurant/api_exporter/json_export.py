"""
JSON Exporter

Generates

docs/API_REFERENCE.json
"""

import json
from pathlib import Path


# ==========================================================
# JSON Export
# ==========================================================

def export_json(
    *,
    endpoints,
    docs_dir,
):
    """
    Export API metadata as JSON.
    """

    output = build_json(
        endpoints,
    )

    output_file = (
        Path(docs_dir)
        / "API_REFERENCE.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(

            output,

            f,

            indent=4,

            ensure_ascii=False,

        )

    return output_file


# ==========================================================
# Build JSON
# ==========================================================

def build_json(
    endpoints,
):
    """
    Build the JSON structure.
    """

    apps = {}

    for endpoint in endpoints:

        app = endpoint["app"]

        module = endpoint["module"].split(".")[-1]

        if app not in apps:

            apps[app] = {}

        if module not in apps[app]:

            apps[app][module] = []

        apps[app][module].append(

            serialize_endpoint(
                endpoint,
            )

        )

    return {

        "project": "ZenQRMenu",

        "version": "1.0",

        "applications": [

            {

                "name": app,

                "modules": [

                    {

                        "name": module,

                        "endpoints": endpoints,

                    }

                    for module, endpoints

                    in sorted(modules.items())

                ],

            }

            for app, modules

            in sorted(apps.items())

        ],

    }


# ==========================================================
# Endpoint Serializer
# ==========================================================

def serialize_endpoint(
    endpoint,
):
    """
    Convert endpoint metadata
    into JSON.
    """

    return {

        "url":

            "/" + endpoint["url"],

        "methods":

            endpoint["methods"],

        "view":

            endpoint["class_name"],

        "view_type":

            endpoint.get(
                "view_type",
            ),

        "base_class":

            endpoint.get(
                "base_class",
            ),

        "module":

            endpoint["module"],

        "permissions":

            endpoint["permissions"],

        "authentication":

            endpoint["authentication"],

        "serializer":

            endpoint.get(
                "serializer",
            ),

        "serializer_mapping":

            endpoint.get(
                "serializer_mapping",
            ),

        "example_request":

            endpoint.get(
                "example_request",
            ),

        "example_response":

            endpoint.get(
                "example_response",
            ),

    }