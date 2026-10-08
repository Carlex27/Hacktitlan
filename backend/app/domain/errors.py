from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(ApplicationError):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(
            "not_found",
            f"{resource} {identifier!r} no existe",
            status_code=404,
        )


class ConflictError(ApplicationError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=409)

