from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.errors import AppError

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    400: "BadRequest",
    404: "NotFound",
    405: "MethodNotAllowed",
    413: "PayloadTooLarge",
}


def error_response(status_code: int, code: str, detail: str, **extra: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": code, "detail": detail, **extra})


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("%s on %s: %s", exc.code, request.url.path, exc.message)
    return error_response(exc.status_code, exc.code, exc.message, **exc.extra)


async def _handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    code = _HTTP_ERROR_CODES.get(exc.status_code, "HttpError")
    return error_response(exc.status_code, code, str(exc.detail))


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    problems = [
        f"{'.'.join(str(part) for part in err['loc'] if part != 'body')}: {err['msg']}"
        for err in exc.errors()
    ]
    return error_response(422, "ValidationError", "; ".join(problems))


async def _catch_unexpected_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Runs inside the CORS middleware, so the browser can read the 500 body
    # instead of reporting a CORS failure.
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error processing request to %s", request.url.path)
        return error_response(500, "InternalServerError", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    """Register handlers so every error leaves the API as {"error": code, "detail": message}.

    Call this before adding the CORS middleware so CORS wraps the catch-all.
    """
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(HTTPException, _handle_http_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.middleware("http")(_catch_unexpected_errors)
