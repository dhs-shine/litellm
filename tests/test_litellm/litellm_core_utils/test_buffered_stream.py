"""
Tests for the buffered_stream feature.

The buffered_stream feature converts non-streaming (stream=false) requests to
streaming (stream=true) internally, collects all chunks, and assembles them
into a complete ModelResponse. This helps avoid timeouts when backend
inference servers are slow.
"""

import os
import sys
from typing import Any, Iterator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.abspath("../../..")
)  # Adds the parent directory to the system path

import litellm
from litellm.types.utils import (
    Delta,
    ModelResponseStream,
    StreamingChoices,
    Usage,
)


def create_mock_streaming_chunks() -> List[ModelResponseStream]:
    """Create mock streaming chunks for testing."""
    return [
        ModelResponseStream(
            id="chatcmpl-test-123",
            created=1234567890,
            model="test-model",
            object="chat.completion.chunk",
            system_fingerprint=None,
            choices=[
                StreamingChoices(
                    finish_reason=None,
                    index=0,
                    delta=Delta(
                        content="Hello",
                        role="assistant",
                    ),
                    logprobs=None,
                )
            ],
        ),
        ModelResponseStream(
            id="chatcmpl-test-123",
            created=1234567890,
            model="test-model",
            object="chat.completion.chunk",
            system_fingerprint=None,
            choices=[
                StreamingChoices(
                    finish_reason=None,
                    index=0,
                    delta=Delta(
                        content=" World",
                        role=None,
                    ),
                    logprobs=None,
                )
            ],
        ),
        ModelResponseStream(
            id="chatcmpl-test-123",
            created=1234567890,
            model="test-model",
            object="chat.completion.chunk",
            system_fingerprint=None,
            choices=[
                StreamingChoices(
                    finish_reason="stop",
                    index=0,
                    delta=Delta(
                        content=None,
                        role=None,
                    ),
                    logprobs=None,
                )
            ],
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=2,
                total_tokens=12,
            ),
        ),
    ]


class TestBufferedStreamChunkAssembly:
    """Test that buffered_stream correctly assembles chunks."""

    def test_stream_chunk_builder_assembles_content(self):
        """Test that stream_chunk_builder correctly assembles content from chunks."""
        chunks = create_mock_streaming_chunks()

        result = litellm.stream_chunk_builder(chunks=chunks)

        assert result is not None
        assert result.choices[0].message.content == "Hello World"
        assert result.choices[0].finish_reason == "stop"

    def test_stream_chunk_builder_preserves_usage(self):
        """Test that stream_chunk_builder preserves usage information."""
        chunks = create_mock_streaming_chunks()

        result = litellm.stream_chunk_builder(chunks=chunks)

        assert result is not None
        # Usage should be calculated from chunks
        assert result.usage is not None


class TestBufferedStreamParameter:
    """Test that buffered_stream parameter is correctly handled."""

    def test_buffered_stream_parameter_extracted_from_optional_params(self):
        """Test that buffered_stream is correctly extracted from optional_params."""
        from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler

        handler = BaseLLMHTTPHandler()

        # Create minimal mock objects
        mock_provider_config = MagicMock()
        mock_provider_config.should_fake_stream.return_value = False
        mock_provider_config.validate_environment.return_value = {}
        mock_provider_config.get_complete_url.return_value = "https://test.com"
        mock_provider_config.transform_request.return_value = {}
        mock_provider_config.sign_request.return_value = ({}, None)
        mock_provider_config.supports_stream_param_in_request_body = True

        mock_logging_obj = MagicMock()
        mock_model_response = MagicMock()

        # Test that buffered_stream is extracted from optional_params
        optional_params = {"buffered_stream": True}

        with patch.object(
            handler, "_sync_buffered_stream_completion"
        ) as mock_buffered:
            mock_buffered.return_value = mock_model_response

            handler.completion(
                model="test-model",
                messages=[{"role": "user", "content": "test"}],
                api_base="https://test.com",
                custom_llm_provider="openai",
                model_response=mock_model_response,
                encoding=None,
                logging_obj=mock_logging_obj,
                optional_params=optional_params,
                timeout=30.0,
                litellm_params={},
                acompletion=False,
                stream=False,
                provider_config=mock_provider_config,
            )

            # Verify buffered stream method was called
            mock_buffered.assert_called_once()


class TestBufferedStreamIntegration:
    """Integration tests for buffered_stream with mock streaming."""

    def test_sync_buffered_stream_completion_assembles_response(self):
        """Test that _sync_buffered_stream_completion assembles chunks correctly."""
        from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler

        handler = BaseLLMHTTPHandler()
        chunks = create_mock_streaming_chunks()

        # Create mock provider config
        mock_provider_config = MagicMock()
        mock_provider_config.supports_stream_param_in_request_body = True

        mock_logging_obj = MagicMock()
        mock_model_response = litellm.ModelResponse()

        # Mock make_sync_call to return our test chunks
        def mock_chunk_iterator():
            for chunk in chunks:
                yield chunk

        with patch.object(
            handler, "make_sync_call"
        ) as mock_sync_call:
            mock_sync_call.return_value = (mock_chunk_iterator(), {})

            result = handler._sync_buffered_stream_completion(
                custom_llm_provider="openai",
                provider_config=mock_provider_config,
                api_base="https://test.com",
                headers={},
                data={},
                timeout=30.0,
                model="test-model",
                model_response=mock_model_response,
                logging_obj=mock_logging_obj,
                messages=[{"role": "user", "content": "test"}],
                optional_params={},
                litellm_params={},
                encoding=None,
            )

            assert result is not None
            assert result.choices[0].message.content == "Hello World"

    @pytest.mark.asyncio
    async def test_async_buffered_stream_completion_assembles_response(self):
        """Test that _async_buffered_stream_completion assembles chunks correctly."""
        from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler

        handler = BaseLLMHTTPHandler()
        chunks = create_mock_streaming_chunks()

        # Create mock provider config
        mock_provider_config = MagicMock()
        mock_provider_config.supports_stream_param_in_request_body = True

        mock_logging_obj = MagicMock()
        mock_model_response = litellm.ModelResponse()

        # Create async iterator for chunks
        async def mock_async_chunk_iterator():
            for chunk in chunks:
                yield chunk

        with patch.object(
            handler, "make_async_call_stream_helper"
        ) as mock_async_call:
            mock_async_call.return_value = (mock_async_chunk_iterator(), {})

            result = await handler._async_buffered_stream_completion(
                custom_llm_provider="openai",
                provider_config=mock_provider_config,
                api_base="https://test.com",
                headers={},
                data={},
                timeout=30.0,
                model="test-model",
                model_response=mock_model_response,
                logging_obj=mock_logging_obj,
                messages=[{"role": "user", "content": "test"}],
                optional_params={},
                litellm_params={},
                encoding=None,
            )

            assert result is not None
            assert result.choices[0].message.content == "Hello World"
