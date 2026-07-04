"""
==========================================================
restaurant/utils.py

Generic Utility Helpers

These utilities are intentionally independent of
Django models and business logic.

Contents

Part U1
    • Random Helpers
    • Date Helpers

Part U2
    • Decimal Helpers
    • GPS Helpers

Part U3
    • Request Helpers
    • Response Helpers

==========================================================
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

import json
import secrets
import string


# ----------------------------------------------------------
# Random String
# ----------------------------------------------------------

def random_string(
    length=16,
    alphabet=None,
):
    """
    Generate a cryptographically secure random string.
    """

    if length <= 0:
        raise ValueError(
            "length must be greater than zero."
        )

    if alphabet is None:

        alphabet = (

            string.ascii_letters
            + string.digits

        )

    return "".join(

        secrets.choice(alphabet)

        for _ in range(length)

    )


# ----------------------------------------------------------
# UTC Now
# ----------------------------------------------------------

def utc_now():
    """
    Return current UTC datetime.
    """

    return datetime.now(
        timezone.utc
    )
    
    
# ----------------------------------------------------------
# Parse Decimal
# ----------------------------------------------------------

def parse_decimal(
    value,
    default=Decimal("0.00"),
):
    """
    Safely convert any value to Decimal.
    """

    if value in (
        None,
        "",
    ):
        return default

    try:

        return Decimal(
            str(value)
            .replace(",", "")
            .strip()
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
        AttributeError,
    ):

        return default
    
    
    
# ----------------------------------------------------------
# Latitude
# ----------------------------------------------------------

def validate_latitude(
    latitude,
):
    """
    Validate latitude.
    """

    latitude = parse_decimal(latitude)

    if latitude < Decimal("-90"):

        raise ValueError(
            "Latitude cannot be less than -90."
        )

    if latitude > Decimal("90"):

        raise ValueError(
            "Latitude cannot exceed 90."
        )

    return latitude


# ----------------------------------------------------------
# Longitude
# ----------------------------------------------------------

def validate_longitude(
    longitude,
):
    """
    Validate longitude.
    """

    longitude = parse_decimal(longitude)

    if longitude < Decimal("-180"):

        raise ValueError(
            "Longitude cannot be less than -180."
        )

    if longitude > Decimal("180"):

        raise ValueError(
            "Longitude cannot exceed 180."
        )

    return longitude



# ----------------------------------------------------------
# Client IP
# ----------------------------------------------------------

def get_client_ip(request):
    """
    Return the client's IP address.
    """

    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if forwarded:

        return forwarded.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR",
        "",
    )
    
    
    
def safe_json(
    value,
    default=None,
):
    """
    Safely parse JSON.
    """

    if default is None:

        default = {}

    if value is None:

        return default

    if isinstance(
        value,
        (dict, list),
    ):

        return value

    try:

        return json.loads(value)

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):

        return default
    
    
    
    
def build_response(
    success=True,
    message="",
    data=None,
    errors=None,
    **extra,
):
    """
    Standard API response helper.
    """

    response = {

        "success": bool(success),

        "message": message,

    }

    if data is not None:

        response["data"] = data

    if errors is not None:

        response["errors"] = errors

    if extra:

        response.update(extra)

    return response




