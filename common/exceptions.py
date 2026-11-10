"""Every error response carries a human-readable `message` (and `error`) next to DRF's field errors.

The website shows `message`/`detail`/`error` directly, or the first field error.
"""
from rest_framework.views import exception_handler


def _first_message(data):
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        return _first_message(data[0])
    if isinstance(data, dict):
        for key in ("detail", "message", "error", "non_field_errors"):
            if key in data:
                return _first_message(data[key])
        for key, value in data.items():
            text = _first_message(value)
            if text:
                return f"{key}: {text}"
    return ""


def handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    message = _first_message(data) or "Something went wrong."
    if isinstance(data, dict):
        data.setdefault("message", message)
        data.setdefault("error", message)
    elif isinstance(data, list):
        response.data = {"detail": data, "message": message, "error": message}
    return response
