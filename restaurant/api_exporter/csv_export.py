"""
CSV Exporter

Generates

docs/ENDPOINTS.csv
"""

import csv
from pathlib import Path


# ==========================================================
# Export CSV
# ==========================================================

def export_csv(
    *,
    endpoints,
    docs_dir,
):
    """
    Export endpoint metadata to CSV.
    """

    output_file = (
        Path(docs_dir)
        / "ENDPOINTS.csv"
    )

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8",
    ) as csvfile:

        writer = csv.writer(
            csvfile,
        )

        # ==================================================
        # Header
        # ==================================================

        writer.writerow(

            [

                "App",

                "Module",

                "Method",

                "URL",

                "View",

                "View Type",

                "Serializer",

                "Permission",

                "Authentication",

            ]

        )

        # ==================================================
        # Rows
        # ==================================================

        for endpoint in sorted(
            endpoints,
            key=lambda x: (
                x["app"],
                x["module"],
                x["url"],
            ),
        ):

            serializer = endpoint.get(
                "serializer",
                {},
            )

            serializer_name = ""

            if isinstance(
                serializer,
                dict,
            ):

                serializer_name = serializer.get(
                    "name",
                    "",
                )

            for method in endpoint["methods"]:

                writer.writerow(

                    [

                        endpoint["app"],

                        endpoint["module"],

                        method,

                        "/" + endpoint["url"],

                        endpoint["class_name"],

                        endpoint.get(
                            "view_type",
                            "",
                        ),

                        serializer_name,

                        ", ".join(
                            endpoint["permissions"],
                        ),

                        ", ".join(
                            endpoint["authentication"],
                        ),

                    ]

                )

    return output_file