"""Consistent API response helpers.

Every endpoint returns the same envelope:

    {"success": true,  "message": "...", "data": {...}}
    {"success": false, "message": "...", "data": null, "errors": ...}
"""

from typing import Any


def ok(data: Any = None, message: str = "OK") -> dict:
    """Standard success payload."""
    return {"success": True, "message": message, "data": data}


def fail(message: str, errors: Any = None) -> dict:
    """Standard error payload."""
    return {"success": False, "message": message, "data": None, "errors": errors}
