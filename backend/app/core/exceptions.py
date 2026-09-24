"""Domain/application errors that map cleanly to HTTP responses."""

from typing import Any


class AppError(Exception):
    """Raise inside services/routers to return a consistent error envelope.

    Example:
        raise AppError("Product not found", status_code=404)
    """

    def __init__(
        self,
        message: str = "Something went wrong",
        status_code: int = 400,
        errors: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors
