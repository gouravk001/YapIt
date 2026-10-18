from __future__ import annotations


class AppError(Exception):
    """Base for errors whose message is safe to show to API clients."""

    status_code = 500
    code = "InternalServerError"

    def __init__(self, message: str, **extra: str) -> None:
        super().__init__(message)
        self.message = message
        self.extra = extra


class NotFoundError(AppError):
    status_code = 404
    code = "NotFound"


class UnknownTypeError(AppError):
    status_code = 400
    code = "UnknownType"


class TranscriptionError(AppError):
    status_code = 422
    code = "TranscriptionFailed"


class RecordingTooLargeError(AppError):
    status_code = 413
    code = "RecordingTooLarge"


class UnclearAudioError(AppError):
    """The recording decoded fine but the speech could not be made out reliably."""

    status_code = 422
    code = "UnclearAudio"


class NotANoteError(AppError):
    """The input was understood but is not something worth keeping as a note."""

    status_code = 422
    code = "NotANote"


class ModelUnavailableError(AppError):
    status_code = 503
    code = "ModelUnavailable"


class TypeVersionConflictError(AppError):
    code = "TypeVersionConflict"
