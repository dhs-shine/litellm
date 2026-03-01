"""
FileServerLogger — sends StandardLoggingPayload to a remote file storage API.

Designed for use with rust-file-server (POST /v1/files) but compatible with
any API that accepts {path, content, mode} JSON body.

Usage:
    import litellm
    from litellm.integrations.file_server.file_server_logger import FileServerLogger

    file_logger = FileServerLogger()
    litellm.callbacks = [file_logger]

Environment variables:
    FILE_SERVER_URL          (required) Base URL, e.g. http://rust-file-server:8080
    FILE_SERVER_AUTH_TOKEN    (required) Bearer token
    FILE_SERVER_PATH_PREFIX   (optional) Path prefix, e.g. "litellm-logs/"
    FILE_SERVER_WRITE_MODE    (optional) "async" (default) or "sync"
    FILE_SERVER_TIMEOUT       (optional) Request timeout in seconds (default: 5)
"""

import os
import re
import traceback
from datetime import datetime
from typing import Any, Optional, cast

import httpx

from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.types.utils import StandardLoggingPayload

_VALID_WRITE_MODES = {"async", "sync"}
_PATH_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_path_component(value: str) -> str:
    """Replace any character outside [A-Za-z0-9._-] with underscore."""
    sanitized = _PATH_SAFE_RE.sub("_", value)
    return sanitized or "unknown"


class FileServerLogger(CustomLogger):
    def __init__(
        self,
        file_server_url: Optional[str] = None,
        file_server_auth_token: Optional[str] = None,
        file_server_path_prefix: Optional[str] = None,
        file_server_write_mode: Optional[str] = None,
        file_server_timeout: Optional[float] = None,
        **kwargs,
    ) -> None:
        """
        Args:
            file_server_url: Base URL of the file server (e.g. http://rust-file-server:8080)
            file_server_auth_token: Bearer token for authentication
            file_server_path_prefix: Optional path prefix for stored files
            file_server_write_mode: Write mode - "async" (default) or "sync"
            file_server_timeout: HTTP request timeout in seconds (default: 5)
        """
        self.base_url = (
            file_server_url or os.environ.get("FILE_SERVER_URL", "")
        ).rstrip("/")
        self.auth_token = file_server_auth_token or os.environ.get(
            "FILE_SERVER_AUTH_TOKEN", ""
        )
        self.path_prefix = (
            file_server_path_prefix
            if file_server_path_prefix is not None
            else os.environ.get("FILE_SERVER_PATH_PREFIX", "")
        )
        self.write_mode = (
            file_server_write_mode
            or os.environ.get("FILE_SERVER_WRITE_MODE", "async")
        )
        timeout = (
            file_server_timeout
            if file_server_timeout is not None
            else float(os.environ.get("FILE_SERVER_TIMEOUT", "5"))
        )

        if not self.base_url:
            raise ValueError(
                "FILE_SERVER_URL is required. "
                "Set it via environment variable or pass file_server_url parameter."
            )
        if not self.auth_token:
            raise ValueError(
                "FILE_SERVER_AUTH_TOKEN is required. "
                "Set it via environment variable or pass file_server_auth_token parameter."
            )
        # [Fix #4] Validate write_mode at init time
        if self.write_mode not in _VALID_WRITE_MODES:
            raise ValueError(
                f"Invalid FILE_SERVER_WRITE_MODE: {self.write_mode!r}. "
                f"Must be one of {sorted(_VALID_WRITE_MODES)}."
            )

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            },
        )

        super().__init__(**kwargs)
        verbose_logger.debug(
            f"FileServerLogger initialized: url={self.base_url}, "
            f"prefix={self.path_prefix!r}, mode={self.write_mode}"
        )

    # [Fix #2] AsyncClient lifecycle — context manager and explicit close
    async def __aenter__(self) -> "FileServerLogger":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Explicitly close the underlying HTTP client and release connections."""
        await self._client.aclose()

    async def async_log_success_event(
        self, kwargs, response_obj, start_time, end_time
    ):
        """Called on successful LLM API calls."""
        await self._send_payload(kwargs, start_time)

    async def async_log_failure_event(
        self, kwargs, response_obj, start_time, end_time
    ):
        """Called on failed LLM API calls."""
        await self._send_payload(kwargs, start_time)

    async def _send_payload(self, kwargs: dict, start_time: Any) -> None:
        """Extract StandardLoggingPayload and POST to file server."""
        try:
            payload: Optional[StandardLoggingPayload] = cast(
                Optional[StandardLoggingPayload],
                kwargs.get("standard_logging_object", None),
            )

            if payload is None:
                verbose_logger.debug(
                    "FileServerLogger: No standard_logging_object found, skipping"
                )
                return

            file_path = self._build_file_path(payload, start_time)

            # [Fix #3] Safe JSON serialization — handles non-serializable values
            try:
                content_json = safe_dumps(payload)
                import json

                content = json.loads(content_json)
            except Exception as ser_err:
                verbose_logger.error(
                    f"FileServerLogger: Failed to serialize payload — {ser_err}. Skipping."
                )
                return

            response = await self._client.post(
                "/v1/files",
                json={
                    "path": file_path,
                    "content": content,
                    "mode": self.write_mode,
                },
            )
            # [Fix #5] raise_for_status triggers HTTPStatusError which is caught below
            response.raise_for_status()

            verbose_logger.debug(
                f"FileServerLogger: Sent payload to {file_path} "
                f"(status={response.status_code})"
            )

        except httpx.HTTPStatusError as e:
            verbose_logger.error(
                f"FileServerLogger: HTTP error {e.response.status_code} — "
                f"{e.response.text}"
            )
        except Exception:
            verbose_logger.error(
                f"FileServerLogger: Failed to send payload — "
                f"{traceback.format_exc()}"
            )

    def _build_file_path(
        self, payload: StandardLoggingPayload, start_time: Any
    ) -> str:
        """
        Build file path in format: {prefix}{YYYY-MM-DD}/{safe_payload_id}.json

        - payload_id is sanitized to [A-Za-z0-9._-] to prevent path injection.
        - Falls back to current date if start_time is not a datetime.
        """
        if isinstance(start_time, datetime):
            date_str = start_time.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # [Fix #1] Sanitize payload_id to prevent path traversal / injection
        raw_id = str(payload.get("id") or "unknown")
        safe_id = _sanitize_path_component(raw_id)

        return f"{self.path_prefix}{date_str}/{safe_id}.json"
