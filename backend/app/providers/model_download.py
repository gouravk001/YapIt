from __future__ import annotations

import logging

from faster_whisper.utils import download_model  # type: ignore[import-untyped]
from huggingface_hub.errors import LocalEntryNotFoundError

logger = logging.getLogger(__name__)


def ensure_whisper_model(model_name: str) -> str:
    """Return the local path of a Whisper model, downloading it only if it is not cached yet.

    This is the only code allowed to use the network, and only on the first start.
    """
    try:
        return download_model(model_name, local_files_only=True)
    except LocalEntryNotFoundError:
        pass

    logger.info("Whisper model %r is not downloaded yet; downloading it once…", model_name)
    try:
        path = download_model(model_name)
    except Exception as exc:
        raise RuntimeError(
            f"Whisper model {model_name!r} isn't downloaded and couldn't be fetched. "
            "Connect to the internet once and restart; later starts work offline."
        ) from exc
    logger.info("Downloaded Whisper model %r to %s", model_name, path)
    return path
