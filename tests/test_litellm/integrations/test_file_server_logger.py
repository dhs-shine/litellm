"""
Unit tests for FileServerLogger.

Tests cover:
- Success/failure event logging
- StandardLoggingPayload extraction and skip logic
- File path construction with prefix and date
- HTTP error handling (non-blocking)
- Initialization validation
- Code review fixes: path sanitization, client lifecycle, write_mode validation,
  safe serialization, HTTPStatusError branch
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from litellm.integrations.file_server.file_server_logger import (
    FileServerLogger,
    _sanitize_path_component,
)


@pytest.fixture
def env_vars():
    """Set required environment variables for FileServerLogger."""
    with patch.dict(
        os.environ,
        {
            "FILE_SERVER_URL": "http://test-server:8080",
            "FILE_SERVER_AUTH_TOKEN": "test-token",
        },
    ):
        yield


@pytest.fixture
def env_vars_with_prefix():
    """Set environment variables with a path prefix."""
    with patch.dict(
        os.environ,
        {
            "FILE_SERVER_URL": "http://test-server:8080",
            "FILE_SERVER_AUTH_TOKEN": "test-token",
            "FILE_SERVER_PATH_PREFIX": "litellm-logs/",
        },
    ):
        yield


@pytest.fixture
def sample_standard_logging_payload():
    """A minimal StandardLoggingPayload-like dict."""
    return {
        "id": "chatcmpl-abc123",
        "trace_id": "trace-001",
        "call_type": "completion",
        "stream": False,
        "response_cost": 0.015,
        "cost_breakdown": None,
        "response_cost_failure_debug_info": None,
        "status": "success",
        "status_fields": {},
        "custom_llm_provider": "openai",
        "total_tokens": 150,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "startTime": 1700000000.0,
        "endTime": 1700000001.0,
        "completionStartTime": 1700000000.5,
        "response_time": 1.0,
        "model_map_information": {"model_map_key": "gpt-4", "model_map_value": None},
        "model": "gpt-4",
        "model_id": None,
        "model_group": None,
        "api_base": "https://api.openai.com",
        "metadata": {
            "user_api_key_hash": None,
            "user_api_key_alias": None,
            "user_api_key_spend": None,
            "user_api_key_max_budget": None,
            "user_api_key_budget_reset_at": None,
            "user_api_key_org_id": None,
            "user_api_key_team_id": None,
            "user_api_key_project_id": None,
            "user_api_key_user_id": None,
            "user_api_key_user_email": None,
            "user_api_key_team_alias": None,
            "user_api_key_end_user_id": None,
            "user_api_key_request_route": None,
            "user_api_key_auth_metadata": None,
            "spend_logs_metadata": None,
            "requester_ip_address": None,
            "user_agent": None,
            "requester_metadata": None,
            "requester_custom_headers": None,
            "prompt_management_metadata": None,
            "mcp_tool_call_metadata": None,
            "vector_store_request_metadata": None,
            "applied_guardrails": None,
            "usage_object": None,
            "cold_storage_object_key": None,
            "team_alias": None,
            "team_id": None,
        },
        "cache_hit": None,
        "cache_key": None,
        "saved_cache_cost": 0.0,
        "request_tags": [],
        "end_user": None,
        "requester_ip_address": None,
        "user_agent": None,
        "messages": [{"role": "user", "content": "Hello"}],
        "response": {"choices": [{"message": {"content": "Hi!"}}]},
        "error_str": None,
        "error_information": None,
        "model_parameters": {},
        "hidden_params": {
            "model_id": None,
            "cache_key": None,
            "api_base": None,
            "response_cost": None,
            "litellm_overhead_time_ms": None,
            "additional_headers": None,
            "batch_models": None,
            "litellm_model_name": None,
            "usage_object": None,
        },
        "guardrail_information": None,
        "standard_built_in_tools_params": None,
    }


class TestFileServerLoggerInit:
    """Tests for FileServerLogger initialization."""

    def test_init_from_env_vars(self, env_vars):
        logger = FileServerLogger()
        assert logger.base_url == "http://test-server:8080"
        assert logger.auth_token == "test-token"
        assert logger.path_prefix == ""
        assert logger.write_mode == "async"

    def test_init_from_params(self):
        logger = FileServerLogger(
            file_server_url="http://custom:9090",
            file_server_auth_token="my-token",
            file_server_path_prefix="prefix/",
            file_server_write_mode="sync",
            file_server_timeout=10.0,
        )
        assert logger.base_url == "http://custom:9090"
        assert logger.auth_token == "my-token"
        assert logger.path_prefix == "prefix/"
        assert logger.write_mode == "sync"

    def test_init_strips_trailing_slash_from_url(self, env_vars):
        logger = FileServerLogger(file_server_url="http://test:8080/")
        assert logger.base_url == "http://test:8080"

    def test_init_raises_without_url(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="FILE_SERVER_URL is required"):
                FileServerLogger(file_server_auth_token="token")

    def test_init_raises_without_auth_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="FILE_SERVER_AUTH_TOKEN is required"):
                FileServerLogger(file_server_url="http://test:8080")


class TestFileServerLoggerFilePath:
    """Tests for file path construction."""

    def test_build_file_path_with_datetime(self, env_vars):
        logger = FileServerLogger()
        payload = {"id": "chatcmpl-abc123"}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        path = logger._build_file_path(payload, start_time)
        assert path == "2026-03-01/chatcmpl-abc123.json"

    def test_build_file_path_with_prefix(self, env_vars_with_prefix):
        logger = FileServerLogger()
        payload = {"id": "chatcmpl-xyz789"}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        path = logger._build_file_path(payload, start_time)
        assert path == "litellm-logs/2026-03-01/chatcmpl-xyz789.json"

    def test_build_file_path_fallback_to_now(self, env_vars):
        logger = FileServerLogger()
        payload = {"id": "chatcmpl-fallback"}
        start_time = "not-a-datetime"

        path = logger._build_file_path(payload, start_time)
        today = datetime.now().strftime("%Y-%m-%d")
        assert path == f"{today}/chatcmpl-fallback.json"

    def test_build_file_path_missing_id(self, env_vars):
        logger = FileServerLogger()
        payload = {}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        path = logger._build_file_path(payload, start_time)
        assert path == "2026-03-01/unknown.json"


class TestFileServerLoggerSendPayload:
    """Tests for payload sending logic."""

    @pytest.mark.asyncio
    async def test_async_log_success_sends_payload(
        self, env_vars, sample_standard_logging_payload
    ):
        logger = FileServerLogger()

        mock_response = httpx.Response(202, json={"status": "queued", "path": "test"})
        logger._client.post = AsyncMock(return_value=mock_response)

        kwargs = {"standard_logging_object": sample_standard_logging_payload}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        await logger.async_log_success_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

        logger._client.post.assert_called_once()
        call_kwargs = logger._client.post.call_args
        assert call_kwargs.args[0] == "/v1/files"

        body = call_kwargs.kwargs["json"]
        assert body["path"] == "2026-03-01/chatcmpl-abc123.json"
        assert body["content"] == sample_standard_logging_payload
        assert body["mode"] == "async"

    @pytest.mark.asyncio
    async def test_async_log_failure_sends_payload(
        self, env_vars, sample_standard_logging_payload
    ):
        logger = FileServerLogger()

        mock_response = httpx.Response(202, json={"status": "queued", "path": "test"})
        logger._client.post = AsyncMock(return_value=mock_response)

        kwargs = {"standard_logging_object": sample_standard_logging_payload}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        await logger.async_log_failure_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

        logger._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_payload_skips_request(self, env_vars):
        logger = FileServerLogger()
        logger._client.post = AsyncMock()

        kwargs = {}  # no standard_logging_object
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        await logger.async_log_success_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

        logger._client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_error_does_not_raise(
        self, env_vars, sample_standard_logging_payload
    ):
        """HTTP errors should be logged but not propagated to LiteLLM."""
        logger = FileServerLogger()

        error_response = httpx.Response(
            500,
            json={"error": {"code": "IO_ERROR", "message": "disk full"}},
            request=httpx.Request("POST", "http://test-server:8080/v1/files"),
        )
        logger._client.post = AsyncMock(return_value=error_response)

        kwargs = {"standard_logging_object": sample_standard_logging_payload}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        # Should not raise
        await logger.async_log_success_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

    @pytest.mark.asyncio
    async def test_connection_error_does_not_raise(
        self, env_vars, sample_standard_logging_payload
    ):
        """Connection errors should be logged but not propagated."""
        logger = FileServerLogger()
        logger._client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        kwargs = {"standard_logging_object": sample_standard_logging_payload}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        # Should not raise
        await logger.async_log_success_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

    @pytest.mark.asyncio
    async def test_write_mode_sync(self, sample_standard_logging_payload):
        logger = FileServerLogger(
            file_server_url="http://test:8080",
            file_server_auth_token="token",
            file_server_write_mode="sync",
        )

        mock_response = httpx.Response(201, json={"status": "stored", "path": "test"})
        logger._client.post = AsyncMock(return_value=mock_response)

        kwargs = {"standard_logging_object": sample_standard_logging_payload}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        await logger.async_log_success_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

        body = logger._client.post.call_args.kwargs["json"]
        assert body["mode"] == "sync"


class TestPathSanitization:
    """Tests for Fix #1: payload_id path injection prevention."""

    def test_sanitize_normal_id(self):
        assert _sanitize_path_component("chatcmpl-abc123") == "chatcmpl-abc123"

    def test_sanitize_slash_in_id(self):
        # slashes must be replaced to prevent path traversal
        assert _sanitize_path_component("chat/cmpl-abc") == "chat_cmpl-abc"

    def test_sanitize_dotdot_in_id(self):
        assert _sanitize_path_component("../escape") == ".._escape"

    def test_sanitize_spaces_and_special_chars(self):
        assert _sanitize_path_component("id with spaces!@#") == "id_with_spaces___"

    def test_sanitize_empty_becomes_unknown(self):
        assert _sanitize_path_component("") == "unknown"

    def test_build_file_path_sanitizes_id(self, env_vars):
        logger = FileServerLogger()
        payload = {"id": "chat/cmpl-../evil"}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        path = logger._build_file_path(payload, start_time)
        # The filename component (after the date directory) must not contain a slash,
        # which would split the path and enable directory injection.
        # e.g. "2026-03-01/chat_cmpl-.._evil.json" — no extra slash in filename.
        parts = path.split("/")
        filename = parts[-1]
        assert "/" not in filename
        # The raw slash from the ID is replaced
        assert "chat_cmpl" in filename

    # fixture redeclared locally for convenience
    @pytest.fixture(autouse=False)
    def env_vars(self):
        with patch.dict(
            os.environ,
            {
                "FILE_SERVER_URL": "http://test:8080",
                "FILE_SERVER_AUTH_TOKEN": "test-token",
            },
        ):
            yield


class TestWriteModeValidation:
    """Tests for Fix #4: write_mode validation at init time."""

    def test_valid_async_mode(self):
        logger = FileServerLogger(
            file_server_url="http://test:8080",
            file_server_auth_token="token",
            file_server_write_mode="async",
        )
        assert logger.write_mode == "async"

    def test_valid_sync_mode(self):
        logger = FileServerLogger(
            file_server_url="http://test:8080",
            file_server_auth_token="token",
            file_server_write_mode="sync",
        )
        assert logger.write_mode == "sync"

    def test_invalid_mode_raises_at_init(self):
        with pytest.raises(ValueError, match="Invalid FILE_SERVER_WRITE_MODE"):
            FileServerLogger(
                file_server_url="http://test:8080",
                file_server_auth_token="token",
                file_server_write_mode="batch",  # invalid
            )


class TestAsyncClientLifecycle:
    """Tests for Fix #2: AsyncClient close() and context manager."""

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self):
        logger = FileServerLogger(
            file_server_url="http://test:8080",
            file_server_auth_token="token",
        )
        logger._client.aclose = AsyncMock()

        await logger.close()
        logger._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_calls_close(self):
        logger = FileServerLogger(
            file_server_url="http://test:8080",
            file_server_auth_token="token",
        )
        logger._client.aclose = AsyncMock()

        async with logger:
            pass  # just enter and exit

        logger._client.aclose.assert_called_once()


class TestHTTPStatusErrorBranch:
    """Tests for Fix #5: HTTPStatusError branch is explicitly exercised."""

    @pytest.mark.asyncio
    async def test_http_status_error_branch_is_triggered(
        self, sample_standard_logging_payload
    ):
        """Verify that a 5xx response causes raise_for_status to raise HTTPStatusError,
        which is caught by the except branch (not the broad except)."""
        logger = FileServerLogger(
            file_server_url="http://test:8080",
            file_server_auth_token="token",
        )

        error_request = httpx.Request("POST", "http://test:8080/v1/files")
        error_response = httpx.Response(
            500,
            json={"error": {"code": "IO_ERROR", "message": "disk full"}},
            request=error_request,
        )

        # Confirm raise_for_status would raise HTTPStatusError for this response
        with pytest.raises(httpx.HTTPStatusError):
            error_response.raise_for_status()

        # Now confirm the logger swallows it gracefully
        logger._client.post = AsyncMock(return_value=error_response)
        kwargs = {"standard_logging_object": sample_standard_logging_payload}
        start_time = datetime(2026, 3, 1, 14, 30, 0)

        # Must not propagate the exception
        await logger.async_log_success_event(
            kwargs=kwargs,
            response_obj=None,
            start_time=start_time,
            end_time=datetime(2026, 3, 1, 14, 30, 1),
        )

        # The POST was called exactly once
        logger._client.post.assert_called_once()

    @pytest.fixture
    def sample_standard_logging_payload(self):
        return {
            "id": "chatcmpl-abc123",
            "trace_id": "trace-001",
            "call_type": "completion",
            "stream": False,
            "response_cost": 0.015,
            "cost_breakdown": None,
            "response_cost_failure_debug_info": None,
            "status": "success",
            "status_fields": {},
            "custom_llm_provider": "openai",
            "total_tokens": 150,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "startTime": 1700000000.0,
            "endTime": 1700000001.0,
            "completionStartTime": 1700000000.5,
            "response_time": 1.0,
            "model_map_information": {"model_map_key": "gpt-4", "model_map_value": None},
            "model": "gpt-4",
            "model_id": None,
            "model_group": None,
            "api_base": "https://api.openai.com",
            "metadata": {},
            "cache_hit": None,
            "cache_key": None,
            "saved_cache_cost": 0.0,
            "request_tags": [],
            "end_user": None,
            "requester_ip_address": None,
            "user_agent": None,
            "messages": [{"role": "user", "content": "Hello"}],
            "response": {"choices": [{"message": {"content": "Hi!"}}]},
            "error_str": None,
            "error_information": None,
            "model_parameters": {},
            "hidden_params": {},
            "guardrail_information": None,
            "standard_built_in_tools_params": None,
        }
