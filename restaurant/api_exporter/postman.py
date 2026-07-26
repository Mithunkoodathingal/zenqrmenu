"""
Postman Collection Exporter

Phase 4.3.1a

Generates the collection skeleton.

POSTMAN_COLLECTION.json
"""

import json
from pathlib import Path
from datetime import datetime


# ==========================================================
# Export Postman Collection
# ==========================================================

def export_postman(
    *,
    endpoints,
    docs_dir,
):
    """
    Export a Postman collection skeleton.
    """

    collection = build_collection(
        endpoints,
    )

    output_file = (
        Path(docs_dir)
        / "POSTMAN_COLLECTION.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            collection,
            f,
            indent=4,
            ensure_ascii=False,
        )

    return output_file


# ==========================================================
# Build Collection
# ==========================================================

def build_collection(
    endpoints,
):
    """
    Build the Postman collection structure.
    """

    grouped = group_endpoints(
        endpoints,
    )

    return {

        "info": build_info(),

        "variable": build_variables(),

        "item": build_root_items(
            grouped,
        ),

    }


# ==========================================================
# Collection Info
# ==========================================================

def build_info():
    """
    Collection metadata.
    """

    return {

        "_postman_id": "",

        "name": "ZenQRMenu API",

        "description": (
            "Automatically generated "
            "Postman Collection."
        ),

        "schema": (
            "https://schema.getpostman.com/"
            "json/collection/v2.1.0/"
            "collection.json"
        ),

    }


# ==========================================================
# Collection Variables
# ==========================================================

def build_variables():
    """
    Global Postman variables.
    """

    return [

        {

            "key": "base_url",

            "value": "http://localhost:8000",

            "type": "string",

        },

        {

            "key": "access_token",

            "value": "",

            "type": "string",

        },

        {

            "key": "refresh_token",

            "value": "",

            "type": "string",

        },

        {

            "key": "restaurant_id",

            "value": "1",

            "type": "string",

        },

        {

            "key": "staff_id",

            "value": "1",

            "type": "string",

        },

        {

            "key": "order_id",

            "value": "1",

            "type": "string",

        },

    ]


# ==========================================================
# Group Endpoints
# ==========================================================

def group_endpoints(
    endpoints,
):
    """
    Group by

    App

        Module

            Endpoints
    """

    grouped = {}

    for endpoint in endpoints:

        app = endpoint["app"]

        module = endpoint["module"].split(".")[-1]

        grouped.setdefault(
            app,
            {},
        )

        grouped[app].setdefault(
            module,
            [],
        )

        grouped[app][module].append(
            endpoint,
        )

    return grouped


# ==========================================================
# Root Folder Structure
# ==========================================================

def build_root_items(
    grouped,
):
    """
    Build the root Postman folders.

    Phase 4.3.1a only creates the
    folder hierarchy.

    Requests are added in Phase 4.3.1b.
    """

    items = []

    for app in sorted(grouped):

        app_folder = {

            "name": app.title(),

            "description": (
                f"{app.title()} APIs"
            ),

            "item": [],

        }

        for module in sorted(
            grouped[app]
        ):

            module_folder = {

                "name": module.replace(
                    "_",
                    " ",
                ).title(),

                "description": (
                    f"{module.title()} endpoints"
                ),

                "item": [],

            }

            app_folder["item"].append(
                module_folder,
            )

        items.append(
            app_folder,
        )

    return items