from __future__ import annotations


class AppError(Exception):
    """Base for errors whose message is safe to show to API clients."""

    status_code = 500
    code = "InternalServerError"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "NotFound"


class UnknownTypeError(AppError):
    status_code = 400
    code = "UnknownType"


class TranscriptionError(AppError):
    status_code = 422
    code = "TranscriptionFailed"


class ModelUnavailableError(AppError):
    status_code = 503
    code = "ModelUnavailable"


class TypeVersionConflictError(AppError):
    code = "TypeVersionConflict"
