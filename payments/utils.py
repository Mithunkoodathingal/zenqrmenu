import os

from cryptography.fernet import Fernet

from django.conf import settings

import json

from decimal import Decimal, InvalidOperation


FERNET = Fernet(
    settings.PAYMENT_ENCRYPTION_KEY.encode()
)


def encrypt(value: str):

    if not value:
        return ""

    return FERNET.encrypt(
        value.encode()
    ).decode()


def decrypt(value: str):

    if not value:
        return ""

    return FERNET.decrypt(
        value.encode()
    ).decode()

"""
payments/utils.py

Part U1 - Random & Date Helpers

Generic utility functions.
These helpers do not import Django models or application code.
"""

import secrets
import string
from datetime import datetime, timezone


# ----------------------------------------------------------
# Random String
# ----------------------------------------------------------

def random_string(
    length=16,
    alphabet=None,
):
    """
    Generate a cryptographically secure random string.

    Example:
        random_string()
        random_string(8)
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
# Random Digits
# ----------------------------------------------------------

def random_digits(
    length=6,
):
    """
    Generate a cryptographically secure
    numeric string.

    Example:
        random_digits()
        random_digits(4)
    """

    if length <= 0:
        raise ValueError(
            "length must be greater than zero."
        )

    digits = string.digits

    return "".join(
        secrets.choice(digits)
        for _ in range(length)
    )


# ----------------------------------------------------------
# UTC Now
# ----------------------------------------------------------

def utc_now():
    """
    Return the current UTC datetime.

    Returns
    -------
    datetime
    """

    return datetime.now(
        timezone.utc
    )


"""
payments/utils.py

Part U2 - Request & Parsing Helpers

Generic utility functions.
"""

# ----------------------------------------------------------
# Client IP
# ----------------------------------------------------------

def get_client_ip(request):
    """
    Return the best client IP from a request.
    """

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR",
        "",
    )


# ----------------------------------------------------------
# Parse Decimal
# ----------------------------------------------------------

def parse_decimal(
    value,
    default=Decimal("0.00"),
):
    """
    Safely parse any value into Decimal.
    """

    if value in (
        None,
        "",
    ):
        return default

    try:
        return Decimal(
            str(value).replace(",", "").strip()
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
        AttributeError,
    ):
        return default


# ----------------------------------------------------------
# Safe JSON
# ----------------------------------------------------------

def safe_json(
    value,
    default=None,
):
    """
    Safely decode JSON.

    Returns default on failure.
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


"""
payments/utils.py

Part U3 - Response & Notification Helpers

Generic utility functions.
These helpers do not depend on application models.
"""

from typing import Any, Dict, Iterable, Optional


# ----------------------------------------------------------
# Build Response
# ----------------------------------------------------------

def build_response(
    success: bool = True,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
    errors: Optional[Any] = None,
    **extra,
):
    """
    Build a consistent API response dictionary.

    Example:
        return Response(
            build_response(
                success=True,
                message="Payment created.",
                data={"id": 1},
            )
        )
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


# ----------------------------------------------------------
# Send Notification
# ----------------------------------------------------------

def send_notification(
    *,
    email_callable=None,
    sms_callable=None,
    whatsapp_callable=None,
    email_kwargs=None,
    sms_kwargs=None,
    whatsapp_kwargs=None,
):
    """
    Generic notification dispatcher.

    This helper intentionally knows nothing about
    Django models or third-party providers.

    Pass provider callables such as:

        send_notification(
            email_callable=send_email,
            email_kwargs={...},
        )

    Returns
    -------
    dict
    """

    results = {}

    channels = (
        ("email", email_callable, email_kwargs),
        ("sms", sms_callable, sms_kwargs),
        ("whatsapp", whatsapp_callable, whatsapp_kwargs),
    )

    for name, func, kwargs in channels:

        if func is None:
            continue

        try:
            results[name] = {
                "success": True,
                "result": func(**(kwargs or {})),
            }

        except Exception as exc:
            results[name] = {
                "success": False,
                "error": str(exc),
            }

    return results
