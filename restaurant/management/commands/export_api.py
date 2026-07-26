import json

import re

from pathlib import Path

import platform

import django

from django.conf import settings

from django.core.management.base import BaseCommand

from django.urls import URLPattern

from django.urls import URLResolver

from django.urls import get_resolver

from collections import defaultdict

from datetime import datetime

from rest_framework import serializers

from rest_framework.views import APIView

from rest_framework.generics import GenericAPIView

from rest_framework.viewsets import ViewSet

from rest_framework.viewsets import GenericViewSet

from rest_framework.viewsets import ModelViewSet

from rest_framework.viewsets import ReadOnlyModelViewSet

from restaurant.api_exporter.postman import (
    export_postman,
)

from restaurant.api_exporter.csv_export import (
    export_csv,
)

from restaurant.api_exporter.json_export import (
    export_json,
    serialize_endpoint,
)

# ==========================================================
# Export API Command
# ==========================================================

class Command(BaseCommand):

    help = "Export registered API endpoints."

    # ======================================================
    # Entry Point
    # ======================================================

    def handle(self, *args, **options):

        resolver = get_resolver()

        endpoints = []

        self.collect_urls(
            resolver.url_patterns,
            prefix="",
            endpoints=endpoints,
        )

        docs_dir = Path(settings.BASE_DIR) / "docs"

        docs_dir.mkdir(
            exist_ok=True,
        )

        output_file = docs_dir / "URLS.txt"
        
        self.generate_markdown(
            
            endpoints=endpoints,
            
            docs_dir=docs_dir,
            
        )
        
        export_json(

            endpoints=endpoints,

            docs_dir=docs_dir,

        )
        
        export_csv(

            endpoints=endpoints,

            docs_dir=docs_dir,

        )
        
        postman_file = export_postman(

            endpoints=endpoints,

            docs_dir=docs_dir,

        )

        with open(
            
            output_file,
            
            "w",
            
            encoding="utf-8",
            
        ) as f:

            for endpoint in endpoints:

                f.write(
                    "=" * 80 + "\n"
                )

                f.write(
                    f"URL               : {endpoint['url']}\n"
                )

                f.write(
                    f"Methods           : {', '.join(endpoint['methods'])}\n"
                )

                f.write(
                    f"View              : {endpoint['view_name']}\n"
                )

                f.write(
                    f"Module            : {endpoint['module']}\n"
                )

                f.write(
                    f"Class             : {endpoint['class_name']}\n"
                )

                f.write(
                    f"Permissions       : {', '.join(endpoint['permissions'])}\n"
                )

                f.write(
                    f"Authentication    : {', '.join(endpoint['authentication'])}\n\n"
                )
                
                
                output_file = "exported_api"  # Base filename without extension

                # Create file paths
                markdown_file = f"{output_file}.md"
                
                json_file = f"{output_file}.json"
                
                csv_file = f"{output_file}.csv"
                
                postman_file = f"{output_file}.postman_collection.json"
                

                generated_files = [
                    
                    markdown_file,
                    
                    json_file,
                    
                    csv_file,
                    
                    postman_file,
                    
                ]
                
                self.stdout.write(

                    self.style.SUCCESS(

                        f"\nExported "

                        f"{len(endpoints)} "

                        f"endpoints.\n"

                        f"Saved to "

                        f"{output_file}"

                    )

                )
                
                self.stdout.write(

                    self.style.SUCCESS(

                        f"Created: {postman_file}"

                    )

                )
                


                for file in generated_files:

                    self.stdout.write(

                        self.style.SUCCESS(

                            f"Created: {file}"

                        )

                    )
        
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

        module_count = 0

        for endpoint in endpoints:

            app = endpoint["app"]

            module = endpoint["module"].split(".")[-1]

            if app not in apps:

                apps[app] = {}

            if module not in apps[app]:

                apps[app][module] = {}

                module_count += 1

            apps[app][module].setdefault(
                "endpoints",
                [],
            )

            apps[app][module]["endpoints"].append(

                serialize_endpoint(
                    endpoint,
                )

            )

        return {

            # ==================================================
            # Metadata
            # ==================================================

            "metadata": {

                "project":
                    "ZenQRMenu",

                "version":
                    "1.0",

                "generated_at":
                    datetime.utcnow().isoformat() + "Z",

                "framework":
                    "Django",
                    
                "framework_version": 
                    django.get_version(),

                "api_framework":
                    "Django REST Framework",

                "python":platform.python_version(),
                    

                "applications":
                    len(apps),

                "modules":
                    module_count,

                "endpoints":
                    len(endpoints),

                "generator":
                    "ZenQRMenu API Exporter",

            },

            # ==================================================
            # Applications
            # ==================================================

            "applications": [

                {

                    "name":
                        app,

                    "module_count":
                        len(modules),

                    "endpoint_count":

                        sum(

                            len(
                                module["endpoints"]
                            )

                            for module

                            in modules.values()

                        ),

                    "modules": [

                        {

                            "name":
                                module_name,

                            "endpoint_count":

                                len(
                                    module["endpoints"]
                                ),

                            "endpoints":

                                module["endpoints"],

                        }

                        for module_name, module

                        in sorted(
                            modules.items()
                        )

                    ],

                }

                for app, modules

                in sorted(
                    apps.items()
                )

            ],

        }

    # ======================================================
    # Recursive URL Scanner
    # ======================================================

    def collect_urls(
        self,
        patterns,
        prefix,
        endpoints,
    ):

        for pattern in patterns:

            # ---------------------------------------------
            # Nested include(...)
            # ---------------------------------------------

            if isinstance(
                pattern,
                URLResolver,
            ):

                self.collect_urls(

                    pattern.url_patterns,

                    prefix + str(
                        pattern.pattern
                    ),

                    endpoints,

                )

                continue

            if not isinstance(
                pattern,
                URLPattern,
            ):

                continue

            callback = pattern.callback

            view_class = getattr(
                callback,
                "view_class",
                None,
            )

            endpoint = {

                "url":
                    prefix
                    + str(pattern.pattern),

                "methods":
                    self.get_http_methods(
                        view_class,
                    ),

                "view_name":
                    callback.__module__
                    + "."
                    + callback.__name__,

                "module":
                    callback.__module__,

                "app":
                    callback.__module__.split(".")[0],

                "class_name":
                    (
                        view_class.__name__
                        if view_class
                        else "Function View"
                    ),

                "view_type":
                    self.get_view_type(
                        view_class,
                    ),

                "base_class":
                    self.get_base_class(
                        view_class,
                    ),
                    
                "example_response":
                    self.build_example_response(
                        view_class,
                    ),
                    
                "example_request":
                    self.build_example_request(
                        view_class,
                    ),

                "serializer":
                    self.get_serializer_info(
                        view_class,
                    ),
                    
                "serializer_mapping":
                    self.get_serializer_mapping(
                        view_class,
                    ),
                    
                "permissions":
                    self.get_permissions(
                        view_class,
                    ),

                "authentication":
                    self.get_authentication(
                        view_class,
                    ),
                    
                "serializer":
                    self.get_serializer_info(
                        view_class,
                    ),

            }

            endpoints.append(
                endpoint,
            )
            
            
    # ==========================================================
    # Root Folder Structure
    # ==========================================================

    def build_root_items(
        self, 
        grouped,
    ):
        """
        Build the complete folder hierarchy.

        App
            └── Module
                    └── Endpoint Requests
        """

        items = []

        for app_name in sorted(grouped):

            app_folder = {

                "name": app_name.title(),

                "description": (
                    f"{app_name.title()} APIs"
                ),

                "item": [],

            }

            for module_name in sorted(
                grouped[app_name]
            ):

                module_folder = self.build_module_folder(

                    module_name,

                    grouped[app_name][module_name],

                )

                app_folder["item"].append(
                    module_folder,
                )

            items.append(
                app_folder,
            )

        return items
    
    
    # ==========================================================
    # Infer Action
    # ==========================================================

    def infer_action(
        self,
        method,
        parts,
    ):
        """
        Infer the CRUD/action name from
        the HTTP method and URL.
        """

        url = "/".join(parts).lower()

        # ==========================================
        # Authentication
        # ==========================================

        auth_actions = {

            "login": "Login",

            "logout": "Logout",

            "refresh": "Refresh Token",

            "register": "Register",

            "verify": "Verify",

        }

        for key, value in auth_actions.items():

            if key in url:

                return value

        # ==========================================
        # Attendance
        # ==========================================

        custom_actions = {

            "clock-in": "Clock In",

            "clock_out": "Clock Out",

            "clock-out": "Clock Out",

            "break/start": "Start Break",

            "break/end": "End Break",

            "assign": "Assign",

            "prepare": "Mark Preparing",

            "preparing": "Mark Preparing",

            "ready": "Mark Ready",

            "served": "Mark Served",

            "deliver": "Mark Delivered",

            "confirm": "Confirm",

            "cancel": "Cancel",

            "archive": "Archive",

            "restore": "Restore",

            "approve": "Approve",

            "reject": "Reject",

        }

        for key, value in custom_actions.items():

            if key in url:

                return value

        # ==========================================
        # CRUD
        # ==========================================

        has_id = any(

            "<" in part

            or

            "{" in part

            for part

            in parts

        )

        if method == "GET":

            return (
                "Retrieve"
                if has_id
                else "List"
            )

        if method == "POST":

            return "Create"

        if method in [

            "PUT",

            "PATCH",

        ]:

            return "Update"

        if method == "DELETE":

            return "Delete"

        return method.title()
    
    # ==========================================================
    # Request Name
    # ==========================================================

    def build_request_name(
        self,
        endpoint,
        method,
    ):
        """
        Generate a human-friendly request name.
        """

        url = endpoint["url"].strip("/")

        parts = [
            part
            for part in url.split("/")
            if part
        ]

        # Remove API prefix

        if parts and parts[0].lower() == "api":

            parts = parts[1:]

        # Clean path parameters

        clean_parts = []

        for part in parts:

            if (
                "<" in part
                or
                "{" in part
            ):

                continue

            clean_parts.append(
                part.replace(
                    "_",
                    " ",
                ).replace(
                    "-",
                    " ",
                ).title()
            )

        resource = (
            clean_parts[0]
            if clean_parts
            else "Resource"
        )

        action = self.infer_action(
            method,
            parts,
        )

        return f"{action} {resource}"


    # ==========================================================
    # Authorization
    # ==========================================================

    def build_request_auth():
        """
        JWT Bearer Authentication.
        """

        return {

            "type": "bearer",

            "bearer": [

                {

                    "key": "token",

                    "value": "{{access_token}}",

                    "type": "string",

                }

            ],

        }


    # ==========================================================
    # Headers
    # ==========================================================

    def build_request_headers():
        """
        Default request headers.
        """

        return [

            {

                "key": "Accept",

                "value": "application/json",

            },

            {

                "key": "Content-Type",

                "value": "application/json",

            },

        ]


    # ==========================================================
    # URL
    # ==========================================================

    def build_request_url(
        endpoint,
    ):
        """
        Build the Postman URL object.
        """

        url = "/" + endpoint["url"]

        return {

            "raw":

                "{{base_url}}"
                + url,

            "host": [

                "{{base_url}}",

            ],

            "path": [

                part

                for part

                in endpoint["url"].split("/")

                if part

            ],

        }


    # ==========================================================
    # Request Body
    # ==========================================================

    def build_request_body(
        endpoint,
        method,
    ):
        """
        Build request body.
        """

        if method in [

            "GET",

            "DELETE",

            "HEAD",

            "OPTIONS",

        ]:

            return None

        example = endpoint.get(
            "example_request",
        )

        if not example:

            return {

                "mode": "raw",

                "raw": "{}",

                "options": {

                    "raw": {

                        "language": "json",

                    }

                },

            }

        return {

            "mode": "raw",

            "raw": json.dumps(

                example,

                indent=4,

            ),

            "options": {

                "raw": {

                    "language": "json",

                }

            },

        }


    # ==========================================================
    # Description
    # ==========================================================

    def build_request_description(
        endpoint,
    ):
        """
        Request description.
        """

        lines = [

            f"View: {endpoint['class_name']}",

            f"Type: {endpoint.get('view_type','')}",

            "",

            "Automatically generated "

            "by ZenQRMenu.",

        ]

        return "\n".join(
            lines,
        )
    
    # ==========================================================
    # Build Request
    # ==========================================================

    def build_request(
        self,
        endpoint,
        method,
    ):
        """
        Build a Postman request.
        """

        return {

            "name": self.build_request_name(
                endpoint,
                method,
            ),

            "request": {

                "method": method,

                "auth": self.build_request_auth(),

                "header": self.build_request_headers(),

                "url": self.build_request_url(
                    endpoint,
                ),

                "body": self.build_request_body(
                    endpoint,
                    method,
                ),

                "description": self.build_request_description(
                    endpoint,
                ),

            },

            "response": [],

        }
    
    
    # ==========================================================
    # Endpoint Folder
    # ==========================================================

    def build_endpoint_folder(
        self,
        endpoint,
    ):
        """
        One endpoint can support
        multiple HTTP methods.

        Each endpoint becomes
        a folder.

        GET

        POST

        PATCH

        DELETE
        """

        folder = {

            "name":

                endpoint["url"],

            "description":

                endpoint["class_name"],

            "item": [],

        }

        for method in endpoint["methods"]:

            folder["item"].append(

                self.build_request(

                    endpoint,

                    method,

                )

            )

        return folder
            
            
            
    # ==========================================================
    # Module Folder
    # ==========================================================


    def build_module_folder(
        self,
        module_name,
        endpoints,
    ):
        """
        Build one module folder.
        """

        # def build_endpoint_folder(endpoint):
        
        #     """
        #     Build one endpoint folder structure.
        #     """
            
        #     folder = {
        #         "name": endpoint["url"].replace("/", " ").title(),
        #         "description": f"Endpoint: {endpoint['url']}",
        #         "methods": endpoint["methods"],
        #         "item": [],
        #     }
        #     return folder
        
        
        folder = {

            "name": module_name.replace(
                "_",
                " ",
            ).title(),

            "description": (
                f"{module_name.replace('_', ' ').title()} Endpoints"
            ),

            "item": [],

        }

        for endpoint in sorted(

            endpoints,

            key=lambda e: (
                e["url"],
                e["methods"],
            ),

        ):

            folder["item"].append(

                self.build_endpoint_folder(
                    endpoint,
                )

            )

        return folder
            
            
    # ==========================================================
    # Example Response
    # ==========================================================

    def build_example_response(
        self,
        view_class,
    ):
        """
        Generate an example response body
        from the response serializer.
        """

        mapping = self.get_serializer_mapping(
            view_class,
        )

        # ------------------------------------------
        # serializer_map
        # ------------------------------------------

        if "GET" in mapping:

            response = mapping["GET"].get(
                "response"
            )

            if response:

                serializer = getattr(
                    view_class,
                    "response_serializer",
                    None,
                )

                if serializer:

                    return self.build_example_payload(
                        serializer,
                        include_read_only=True,
                    )

        # ------------------------------------------
        # Explicit response serializer
        # ------------------------------------------

        serializer = getattr(
            view_class,
            "response_serializer",
            None,
        )

        if serializer:

            return self.build_example_payload(
                serializer,
                include_read_only=True,
            )

        # ------------------------------------------
        # serializer_class
        # ------------------------------------------

        serializer = getattr(
            view_class,
            "serializer_class",
            None,
        )

        if serializer:

            return self.build_example_payload(
                serializer,
                include_read_only=True,
            )

        return None
            
            
    # ==========================================================
    # Example Request
    # ==========================================================

    def build_example_request(
        self,
        view_class,
    ):
        """
        Generate an example request body
        from the request serializer.
        """

        mapping = self.get_serializer_mapping(
            view_class,
        )

        # ------------------------------------------
        # serializer_map
        # ------------------------------------------

        if "POST" in mapping:

            request_serializer = mapping["POST"].get(
                "request"
            )

            if request_serializer:

                serializer_name = request_serializer["name"]

                serializer_class = getattr(
                    view_class,
                    "request_serializer",
                    None,
                )

                if serializer_class:

                    return self.serializer_to_dict(
                        serializer_class,
                    )

        # ------------------------------------------
        # request_serializer
        # ------------------------------------------

        serializer = getattr(
            view_class,
            "request_serializer",
            None,
        )

        if serializer:

            return self.serializer_to_dict(
                serializer,
            )

        # ------------------------------------------
        # serializer_class
        # ------------------------------------------

        serializer = getattr(
            view_class,
            "serializer_class",
            None,
        )

        if serializer:

            return self.serializer_to_dict(
                serializer,
            )

        return None
            
            
    # ==========================================================
    # Serializer Information
    # ==========================================================

    def get_serializer_info(
        self,
        view_class,
    ):
        """
        Detect serializer information.
        """

        if view_class is None:

            return {

                "name": "Not Applicable",

                "source": None,

            }

        serializer = getattr(
            view_class,
            "serializer_class",
            None,
        )

        if serializer is not None:

            return {

                "name":
                    serializer.__name__,

                "source":
                    "serializer_class",

            }

        if hasattr(
            view_class,
            "get_serializer_class",
        ):

            return {

                "name":
                    "Dynamic",

                "source":
                    "get_serializer_class()",

            }

        return {
            
                "name": "Dynamic",
                
                "module": None,
                
                "source": "get_serializer_class()",
                
                "dynamic": True,
                
            }
            
    # ==========================================================
    # View Type
    # ==========================================================

    def get_view_type(
        self,
        view_class,
    ):
        """
        Detect DRF view type.
        """

        if view_class is None:

            return "Function View"

        if issubclass(
            view_class,
            ReadOnlyModelViewSet,
        ):

            return "ReadOnlyModelViewSet"

        if issubclass(
            view_class,
            ModelViewSet,
        ):

            return "ModelViewSet"

        if issubclass(
            view_class,
            GenericViewSet,
        ):

            return "GenericViewSet"

        if issubclass(
            view_class,
            ViewSet,
        ):

            return "ViewSet"

        if issubclass(
            view_class,
            GenericAPIView,
        ):

            return "GenericAPIView"

        if issubclass(
            view_class,
            APIView,
        ):

            return {

                "type": "APIView",

                "inherits": [
                    cls.__name__
                    for cls
                    in view_class.mro()
                ],

                "is_viewset": False,

                "is_generic": False,

                "is_api_view": True,

            }

        return "Unknown"
    
    # ==========================================================
    # Base Class
    # ==========================================================

    def get_base_class(
        self,
        view_class,
    ):
        """
        Return the direct base class.
        """

        if view_class is None:

            return "Function View"

        bases = view_class.__bases__

        if not bases:

            return "Unknown"

        return bases[0].__name__

    # ======================================================
    # HTTP Methods
    # ======================================================

    def get_http_methods(
        self,
        view_class,
    ):

        if view_class is None:

            return [
                "UNKNOWN",
            ]

        methods = []

        for method in [

            "get",

            "post",

            "put",

            "patch",

            "delete",

            "head",

            "options",

        ]:

            if hasattr(
                view_class,
                method,
            ):

                methods.append(
                    method.upper(),
                )

        if not methods:

            methods.append(
                "UNKNOWN",
            )

        return methods

    # ======================================================
    # Permissions
    # ======================================================

    def get_permissions(
        self,
        view_class,
    ):

        if view_class is None:

            return [
                "Unknown",
            ]

        permission_classes = getattr(
            view_class,
            "permission_classes",
            [],
        )

        if not permission_classes:

            return [
                "AllowAny",
            ]

        return [

            permission.__name__

            for permission

            in permission_classes

        ]

    # ======================================================
    # Authentication
    # ======================================================

    def get_authentication(
        self,
        view_class,
    ):

        if view_class is None:

            return [
                "Default",
            ]

        authentication_classes = getattr(
            view_class,
            "authentication_classes",
            [],
        )

        if not authentication_classes:

            return [
                "Default",
            ]

        return [

            authentication.__name__

            for authentication

            in authentication_classes

        ]
        
    # ==========================================================
    # Generate Markdown Documentation
    # ==========================================================

    def generate_markdown(
        self,
        *,
        endpoints,
        docs_dir,
    ):
        """
        Generate API_REFERENCE.md.
        """

        markdown_file = docs_dir / "API_REFERENCE.md"

        grouped = self.group_endpoints(
            endpoints,
        )

        with open(
            markdown_file,
            "w",
            encoding="utf-8",
        ) as file:

            self.write_document_header(
                file=file,
                endpoints=endpoints,
                grouped=grouped,
            )
            
            self.write_table_of_contents(
                file=file,
                grouped=grouped,
            )

            for app_name in sorted(grouped):

                self.write_app_section(
                    file=file,
                    app_name=app_name,
                    modules=grouped[app_name],
                )

            self.write_footer(
                file=file,
                endpoints=endpoints,
                grouped=grouped,
            )
                
    # ==========================================================
    # Document Header
    # ==========================================================

    def write_document_header(
        self,
        *,
        file,
        endpoints,
        grouped,
    ):
        """
        Write the document header.
        """

        total_apps = len(grouped)

        total_modules = sum(
            len(modules)
            for modules
            in grouped.values()
        )

        self.write_divider(file)
        
        generated_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        file.write(
            "# ZenQRMenu API Reference\n\n"
        )

        file.write(
            "Enterprise Backend Documentation\n\n"
        )

        file.write(
            f"**Generated:** {generated_at}\n\n"
        )

        file.write(
            "**Version:** 1.0\n\n"
        )

        file.write(
            "**Framework:** Django + Django REST Framework\n\n"
        )

        file.write(
            "**Architecture:** Service Layer Architecture\n\n"
        )

        file.write(
            "## Summary\n\n"
        )

        file.write(
            "| Metric | Count |\n"
        )

        file.write(
            "|--------|------:|\n"
        )

        file.write(
            f"| Applications | {total_apps} |\n"
        )

        file.write(
            f"| Modules | {total_modules} |\n"
        )

        file.write(
            f"| Endpoints | {len(endpoints)} |\n"
        )

        file.write(
            "\n---\n\n"
        )

        file.write(
            "## Introduction\n\n"
        )

        file.write(
            "This document is automatically generated by "
            "`python manage.py export_api`.\n\n"
        )

        file.write(
            "It lists all registered REST API endpoints "
            "discovered from the Django URL configuration.\n\n"
        )

        file.write(
            "The documentation includes:\n\n"
        )

        file.write(
            "- HTTP methods\n"
        )

        file.write(
            "- URL patterns\n"
        )

        file.write(
            "- View classes\n"
        )

        file.write(
            "- Permission classes\n"
        )

        file.write(
            "- Authentication classes\n\n"
        )


        
        
    # ==========================================================
    # Table of Contents
    # ==========================================================

    def write_table_of_contents(
        self,
        *,
        file,
        grouped,
    ):
        """
        Write the Markdown table of contents.
        """

        file.write(
            "# Table of Contents\n\n"
        )

        for app_name in sorted(grouped):

            app_anchor = self.make_anchor(
                app_name,
            )

            file.write(
                f"- [{app_name.title()}](#{app_anchor})\n"
            )

            for module_name in sorted(grouped[app_name]):

                module_anchor = self.make_anchor(
                    f"{app_name}-{module_name}",
                )

                file.write(
                    f"  - [{module_name.title()}]"
                    f"(#{module_anchor})\n"
                )

                file.write(
                    "\n---\n\n"
                )
                
                for endpoint in sorted(
                    grouped[app_name][module_name],
                    key=lambda x: x["url"],
                ):

                    endpoint_anchor = self.make_endpoint_anchor(
                        endpoint
                    )

                    methods = ", ".join(
                        endpoint["methods"]
                    )

                    file.write(

                        f"    - "

                        f"[{methods} "

                        f"/{endpoint['url']}]"

                        f"(#{endpoint_anchor})\n"

                    )
    
    
    # ==========================================================
    # Markdown Anchor
    # ==========================================================

    def make_anchor(
        self,
        text,
    ):
        """
        Generate GitHub-compatible anchors.
        """

        return (

            text.lower()

            .replace("_", "-")

            .replace(".", "-")

            .replace("/", "-")

            .replace(" ", "-")

        )
        
        
    # ==========================================================
    # Markdown Divider
    # ==========================================================

    def write_divider(
        self,
        file,
    ):
        """
        Write a standard Markdown divider.
        """

        file.write(
            "\n---\n\n"
        )
        
    # ==========================================================
    # Blank Line
    # ==========================================================

    def blank(
        self,
        file,
        lines=1,
    ):
        """
        Write blank lines.
        """

        file.write(
            "\n" * lines
        )
        
        
        
    # ==========================================================
    # Endpoint Anchor
    # ==========================================================

    def make_endpoint_anchor(
        self,
        endpoint,
    ):
        """
        Generate a unique Markdown anchor for an endpoint.

        Example

        GET /api/staff/

        becomes

        get-api-staff
        """

        methods = "-".join(
            method.lower()
            for method
            in endpoint["methods"]
        )

        url = endpoint["url"]

        url = (
            url
            .replace("<", "")
            .replace(">", "")
            .replace(":", "-")
            .replace("_", "-")
            .replace("/", "-")
            .replace(".", "-")
            .replace("(", "")
            .replace(")", "")
            .replace("{", "")
            .replace("}", "")
        )

        return self.make_anchor(
            f"{endpoint['module']}-{methods}-{url}"
        )
            
    # ==========================================================
    # Group Endpoints
    # ==========================================================

    def group_endpoints(
        self,
        endpoints,
    ):

        grouped = defaultdict(
            lambda: defaultdict(list)
        )

        for endpoint in endpoints:

            module = endpoint["module"]

            parts = module.split(".")

            app = endpoint["app"]

            module_name = (
                parts[-1]
                if len(parts) >= 3
                else "General"
            )

            grouped[
                app
            ][
                module_name
            ].append(
                endpoint
            )

        return grouped
    
    
    # ==========================================================
    # App Statistics
    # ==========================================================

    def get_app_statistics(
        self,
        modules,
    ):
        """
        Calculate statistics for a Django app.
        """

        total_modules = len(modules)

        total_endpoints = 0

        methods = set()

        permissions = set()

        authentication = set()

        views = set()

        for endpoints in modules.values():

            total_endpoints += len(endpoints)

            for endpoint in endpoints:

                methods.update(
                    endpoint["methods"]
                )

                permissions.update(
                    endpoint["permissions"]
                )

                authentication.update(
                    endpoint["authentication"]
                )

                views.add(
                    endpoint["class_name"]
                )

        return {

            "modules":
                total_modules,

            "endpoints":
                total_endpoints,
                
            "urls": len(
                {
                    endpoint["url"]
                    for endpoints in modules.values()
                    for endpoint in endpoints
                }
            ),

            "views":
                len(views),

            "methods":
                sorted(methods),

            "permissions":
                sorted(permissions),

            "authentication":
                sorted(authentication),

        }
        
        
    # ==========================================================
    # Module Statistics
    # ==========================================================

    def get_module_statistics(
        self,
        endpoints,
    ):
        """
        Calculate statistics for a module.
        """

        methods = set()

        permissions = set()

        authentication = set()

        views = set()

        urls = set()

        for endpoint in endpoints:

            methods.update(
                endpoint["methods"],
            )

            permissions.update(
                endpoint["permissions"],
            )

            authentication.update(
                endpoint["authentication"],
            )

            views.add(
                endpoint["class_name"],
            )

            urls.add(
                endpoint["url"],
            )

        return {

            "views":
                len(views),

            "endpoints":
                len(endpoints),

            "urls":
                len(urls),

            "methods":
                sorted(methods),

            "permissions":
                sorted(permissions),

            "authentication":
                sorted(authentication),
                
            "api_views": len({
                e["class_name"]
                for e in endpoints
                if e["class_name"].endswith("APIView")
            }),

            "viewsets": len({
                e["class_name"]
                for e in endpoints
                if "ViewSet" in e["class_name"]
            }),

        }
        
        
    # ==========================================================
    # Write Module Statistics
    # ==========================================================

    def write_module_statistics(
        self,
        *,
        file,
        statistics,
    ):
        """
        Write module statistics.
        """

        file.write(
            "### 📊 Statistics\n\n"
        )

        file.write(
            "| Metric | Value |\n"
        )

        file.write(
            "|--------|------:|\n"
        )

        file.write(
            f"| Endpoints | {statistics['endpoints']} |\n"
        )

        file.write(
            f"| URL Patterns | {statistics['urls']} |\n"
        )

        file.write(
            f"| View Classes | {statistics['views']} |\n"
        )

        file.write(
            f"| HTTP Methods | {', '.join(statistics['methods'])} |\n"
        )

        file.write(
            f"| Permissions | {', '.join(statistics['permissions'])} |\n"
        )

        file.write(
            f"| Authentication | {', '.join(statistics['authentication'])} |\n"
        )

        file.write(
            "\n"
        )
        
        
        
        
        
    # ==========================================================
    # Write App Statistics
    # ==========================================================

    def write_app_statistics(
        self,
        *,
        file,
        statistics,
    ):
        """
        Write statistics for an app.
        """

        file.write(
            "### Statistics\n\n"
        )

        file.write(
            "| Metric | Value |\n"
        )

        file.write(
            "|--------|------:|\n"
        )

        file.write(
            f"| Modules | {statistics['modules']} |\n"
        )

        file.write(
            f"| Views | {statistics['views']} |\n"
        )

        file.write(
            f"| Endpoints | {statistics['endpoints']} |\n"
        )

        file.write(
            f"| HTTP Methods | {', '.join(statistics['methods'])} |\n"
        )

        file.write(
            f"| Permissions | {', '.join(statistics['permissions'])} |\n"
        )

        file.write(
            f"| Authentication | {', '.join(statistics['authentication'])} |\n"
        )
        
        file.write(
            f"| URL Patterns | {statistics['urls']} |\n"
        )

        file.write(
            "\n"
        )
    
    # ==========================================================
    # Write Header
    # ==========================================================

    def write_header(
        self,
        file,
        endpoints,
    ):
        
        self.write_divider(file)
        
        file.write(
            
            "# ZenQRMenu API Reference\n\n"
            
        )

        file.write(
            f"Generated: "
            f"{datetime.now()}\n\n"
        )

        file.write(
            f"Total Endpoints: "
            f"{len(endpoints)}\n\n"
        )

        
    # ==========================================================
    # Write App Section
    # ==========================================================

    def write_app_section(
        self,
        file,
        app_name,
        modules,
    ):

        self.write_divider(file)

        file.write(
            f"# 📦 {app_name.title()}\n\n"
        )

        file.write(
            f'<a id="{self.make_anchor(app_name)}"></a>\n\n'
        )

        statistics = self.get_app_statistics(
            modules,
        )

        self.write_app_statistics(
            file=file,
            statistics=statistics,
        )

        for module in sorted(modules):

                file.write(
                    f"## 📁 {module.replace('_',' ').title()}\n\n"
                )

                file.write(
                    f'<a id="{self.make_anchor(f"{app_name}-{module}")}"></a>\n\n'
                )

                statistics = self.get_module_statistics(
                    modules[module],
                )

                self.write_module_statistics(
                    file=file,
                    statistics=statistics,
                )

                self.write_module_table(
                    file=file,
                    endpoints=modules[module],
                )

                file.write(
                    "\n---\n\n"
                )
            
            
    # ==========================================================
    # Write Endpoint Cards
    # ==========================================================

    def write_module_table(
        self,
        *,
        file,
        endpoints,
    ):
        """
        Write endpoint cards.
        """

        for endpoint in sorted(
            endpoints,
            key=lambda x: x["url"],
        ):

            self.write_endpoint_card(
                file=file,
                endpoint=endpoint,
            )
            
            
    # ==========================================================
    # Write Endpoint Card
    # ==========================================================

    def write_endpoint_card(
        self,
        *,
        file,
        endpoint,
    ):
        
        
        """
        Write a professional endpoint card.
        """
        
        
        serializer_mapping = endpoint["serializer_mapping"]

        file.write(
            "\n### Serializers\n\n"
        )

        example = endpoint["example_request"]

        if example:

            file.write(
                "### Example Request\n\n"
            )
            
            
            response = endpoint["example_response"]

            if response:

                file.write(
                    "### Example Response\n\n"
                )

                file.write(
                    "```json\n"
                )

                file.write(
                    json.dumps(
                        response,
                        indent=4,
                    )
                )

                file.write(
                    "\n```\n\n"
                )
            

            file.write(
                "```json\n"
            )

            file.write(
                json.dumps(
                    example,
                    indent=4,
                )
            )

            file.write(
                "\n```\n\n"
            )
            
        # serializer_map (per HTTP method)

        if "GET" in serializer_mapping or "POST" in serializer_mapping:

            for method in sorted(serializer_mapping):

                serializers = serializer_mapping[method]

                file.write(
                    f"#### {method}\n\n"
                )

                if "request" in serializers:

                    file.write(
                        f"- **Request:** `{serializers['request']['name']}`\n"
                    )

                if "response" in serializers:

                    file.write(
                        f"- **Response:** `{serializers['response']['name']}`\n"
                    )

                file.write("\n")

        else:

            file.write(
                f"- **Request:** `{serializer_mapping['request']['name']}`\n"
            )

            file.write(
                f"- **Response:** `{serializer_mapping['response']['name']}`\n\n"
            )


        anchor = self.make_endpoint_anchor(
            endpoint,
        )

        methods = ", ".join(
            endpoint["methods"],
        )

        permissions = ", ".join(
            endpoint["permissions"],
        )

        authentication = ", ".join(
            endpoint["authentication"],
        )

        file.write(
            f'<a id="{anchor}"></a>\n\n'
        )

        method_badges = " ".join(
            f"`{method}`"
            for method in endpoint["methods"]
        )

        file.write(
            f"## {method_badges}\n\n"
        )

        file.write(
            f"### `/{endpoint['url']}`\n\n"
        )

        file.write(
            "| Property | Value |\n"
        )

        file.write(
            "|:---------|:------|\n"
        )
        
        file.write(
            "> **Endpoint Metadata**\n>\n"
        )

        file.write(
            f"> View: `{endpoint['class_name']}`\n>\n"
        )

        file.write(
            f"> Module: `{endpoint['module']}`\n\n"
        )

        file.write(
            f"| View | `{endpoint['class_name']}` |\n"
        )

        file.write(
            f"| DRF Type | `{endpoint['view_type']}` |\n"
        )

        file.write(
            f"| Base Class | `{endpoint['base_class']}` |\n"
        )
        
        serializer = endpoint["serializer"]

        file.write(
            f"| Serializer | `{serializer['name']}` |\n"
        )
        
        if serializer["source"]:

            file.write(
                f"| Serializer Source | `{serializer['source']}` |\n"
            )

        file.write(
            f"| Module | `{endpoint['module']}` |\n"
        )

        file.write(
            f"| HTTP Methods | `{methods}` |\n"
        )

        file.write(
            f"| Permissions | `{permissions}` |\n"
        )

        file.write(
            f"| Authentication | `{authentication}` |\n"
        )

        file.write(
            "\n"
        )
        
        file.write(
            "#### HTTP Request\n\n"
        )

        file.write(
            "```http\n"
        )

        file.write(
            "#### URL\n\n"
        )
        
        file.write(
            "#### Description\n\n"
        )

        file.write(
            "Automatically discovered endpoint.\n\n"
        )

        file.write(
            "```http\n"
        )

        file.write(
            f"{methods} /{endpoint['url']}\n"
        )

        for method in endpoint["methods"]:

            file.write(
                f"{method} /{endpoint['url']}\n"
            )

        file.write(
            "```\n\n"
        )
        
        
        
    # ==========================================================
    # Footer
    # ==========================================================

    def write_footer(
        self,
        *,
        file,
        endpoints,
        grouped,
    ):
        """
        Write the document footer.
        """

        total_apps = len(grouped)

        total_modules = sum(
            len(modules)
            for modules
            in grouped.values()
        )

        total_endpoints = len(endpoints)

        generated_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.write_divider(
            file,
        )

        file.write(
            "# Document Information\n\n"
        )

        file.write(
            "| Property | Value |\n"
        )

        file.write(
            "|:---------|:------|\n"
        )

        file.write(
            "| Project | ZenQRMenu |\n"
        )

        file.write(
            "| Framework | Django |\n"
        )

        file.write(
            "| API Framework | Django REST Framework |\n"
        )

        file.write(
            "| Documentation | Automatically Generated |\n"
        )

        file.write(
            f"| Generated | {generated_at} |\n"
        )

        file.write(
            f"| Applications | {total_apps} |\n"
        )

        file.write(
            f"| Modules | {total_modules} |\n"
        )

        file.write(
            f"| Endpoints | {total_endpoints} |\n"
        )

        file.write("\n")

        file.write(
            "> **Note**\n>\n"
        )

        file.write(
            "> This document is generated automatically using\n"
        )

        file.write(
            "> `python manage.py export_api`.\n>\n"
        )

        file.write(
            "> Do not edit this file manually.\n\n"
        )

        self.write_divider(
            file,
        )

        file.write(
            "<div align='center'>\n\n"
        )

        file.write(
            "Generated by **ZenQRMenu API Exporter**\n\n"
        )

        file.write(
            "| Python | {} |\n".format(
                platform.python_version()
            )
        )

        file.write(
            "| Django | {} |\n".format(
                django.get_version()
            )
        )

        file.write(
            "Version **1.0**\n\n"
        )

        file.write(
            "</div>\n"
        )
        
    # ==========================================================
    # Request / Response Serializer Information
    # ==========================================================

    def get_serializer_mapping(
        self,
        view_class,
    ):
        """
        Detect request and response serializers declared on the view.

        Detection order

        1. serializer_map
        2. request_serializer / response_serializer
        3. serializer_class
        4. get_serializer_class()
        """

        default = {
            "request": {
                "name": "Not Detected",
                "source": None,
            },
            "response": {
                "name": "Not Detected",
                "source": None,
            },
        }

        if view_class is None:
            return default

        # ------------------------------------------------------
        # serializer_map
        # ------------------------------------------------------

        serializer_map = getattr(
            view_class,
            "serializer_map",
            None,
        )

        if serializer_map:

            mapping = {}

            for method, serializers in serializer_map.items():

                mapping[method.upper()] = {}

                if serializers.get("request"):

                    mapping[method.upper()]["request"] = {

                        "name":
                            serializers["request"].__name__,

                        "source":
                            "serializer_map",

                    }

                if serializers.get("response"):

                    mapping[method.upper()]["response"] = {

                        "name":
                            serializers["response"].__name__,

                        "source":
                            "serializer_map",

                    }

            return mapping

        # ------------------------------------------------------
        # Explicit request / response serializers
        # ------------------------------------------------------

        request_serializer = getattr(
            view_class,
            "request_serializer",
            None,
        )

        response_serializer = getattr(
            view_class,
            "response_serializer",
            None,
        )

        if request_serializer:

            default["request"] = {

                "name":
                    request_serializer.__name__,

                "source":
                    "request_serializer",

            }

        if response_serializer:

            default["response"] = {

                "name":
                    response_serializer.__name__,

                "source":
                    "response_serializer",

            }

        # ------------------------------------------------------
        # serializer_class
        # ------------------------------------------------------

        serializer_class = getattr(
            view_class,
            "serializer_class",
            None,
        )

        if serializer_class:

            serializer = {

                "name":
                    serializer_class.__name__,

                "source":
                    "serializer_class",

            }

            default["request"] = serializer

            default["response"] = serializer

            return default

        # ------------------------------------------------------
        # Dynamic serializer
        # ------------------------------------------------------

        if hasattr(
            view_class,
            "get_serializer_class",
        ):

            serializer = {

                "name":
                    "Dynamic",

                "source":
                    "get_serializer_class()",

            }

            default["request"] = serializer

            default["response"] = serializer

        return default
    
    
    # ==========================================================
    # Serializer → Example JSON
    # ==========================================================

    def build_example_payload(
        self,
        serializer_class,
        include_read_only=False,
    ):
        """
        Convert a serializer into
        an example JSON object.
        """

        serializer = serializer_class(
            context={},
        )

        data = {}

        for name, field in serializer.fields.items():

            if (

                field.read_only

                and

                not include_read_only

            ):

                continue
            

            if getattr(
                field,
                "write_only",
                False,
            ):

                data[name] = "<value>"

                continue


            if isinstance(
                field,
                serializers.ListSerializer,
            ):

                child = field.child

                if isinstance(
                    child,
                    serializers.Serializer,
                ):

                    data[name] = [

                        self.build_example_payload(
                            child.__class__,
                            include_read_only,
                        )

                    ]

                    continue

            if isinstance(
                field,
                serializers.Serializer,
            ):

                data[name] = self.build_example_payload(
                    field.__class__,
                    include_read_only,
                )

                continue

            data[name] = self.get_example_value(
                field,
            )

        return data
    
    # ==========================================================
    # Example Values
    # ==========================================================

    def get_example_value(
        self,
        field,
    ):
        """
        Generate an example value
        for a serializer field.
        """

        from rest_framework import serializers

        if isinstance(
            field,
            serializers.CharField,
        ):
            return "string"

        if isinstance(
            field,
            serializers.EmailField,
        ):
            return "user@example.com"

        if isinstance(
            field,
            serializers.IntegerField,
        ):
            return 0

        if isinstance(
            field,
            serializers.FloatField,
        ):
            return 0.0

        if isinstance(
            field,
            serializers.DecimalField,
        ):
            return "0.00"

        if isinstance(
            field,
            serializers.BooleanField,
        ):
            return False

        if isinstance(
            field,
            serializers.DateField,
        ):
            return "2026-01-01"

        if isinstance(
            field,
            serializers.DateTimeField,
        ):
            return "2026-01-01T12:00:00Z"

        if isinstance(
            field,
            serializers.TimeField,
        ):
            return "09:00:00"

        if isinstance(
            field,
            serializers.ChoiceField,
        ):
            return field.choices and next(iter(field.choices))

        if isinstance(
            field,
            serializers.ListField,
        ):
            return []

        return None