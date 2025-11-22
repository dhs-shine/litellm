
import asyncio
import os
import time
import tracemalloc
from types import SimpleNamespace
from typing import AsyncIterator, Optional, List

# Mocking litellm parts to avoid full setup
import litellm
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse, StreamingChoices, Delta

# Mock logging object
class MockLoggingObject:
    def __init__(self):
        self.model_call_details = {"litellm_params": {}}
        self.call_type = "completion"
        self.completion_start_time = None
        self._llm_caching_handler = None
        self.messages = []
    
    def _update_completion_start_time(self, completion_start_time):
        self.completion_start_time = completion_start_time

    async def async_success_handler(self, *args, **kwargs):
        pass
    
    def success_handler(self, *args, **kwargs):
        pass

    async def async_failure_handler(self, *args, **kwargs):
        pass
        
    def failure_handler(self, *args, **kwargs):
        pass

# Mock stream yielding objects
async def mock_stream(count: int):
    for i in range(count):
        # Create a mock chunk object using real litellm types
        chunk = ModelResponse(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1694268190,
            model="gpt-3.5-turbo-0613",
            choices=[
                StreamingChoices(
                    index=0,
                    delta=Delta(content=f"chunk {i} "),
                    finish_reason=None,
                )
            ],
        )
        yield chunk
        
    yield ModelResponse(
        id="chatcmpl-123",
        object="chat.completion.chunk",
        created=1694268190,
        model="gpt-3.5-turbo-0613",
        choices=[
            StreamingChoices(
                index=0,
                delta=Delta(content=""),
                finish_reason="stop",
            )
        ],
    )

async def run_test(disable_logging: bool):
    print(f"\nRunning test with disable_streaming_logging={disable_logging}")
    litellm.disable_streaming_logging = disable_logging
    
    tracemalloc.start()
    
    logging_obj = MockLoggingObject()
    # Use a smaller number for quick verification, but large enough to show accumulation if present
    stream = mock_stream(5000) 
    
    wrapper = CustomStreamWrapper(
        completion_stream=stream,
        model="gpt-3.5-turbo",
        logging_obj=logging_obj,
        custom_llm_provider="openai"
    )
    
    start_snapshot = tracemalloc.take_snapshot()
    
    i = 0
    async for chunk in wrapper:
        i += 1
        if i % 1000 == 0:
            current_snapshot = tracemalloc.take_snapshot()
            # top_stats = current_snapshot.compare_to(start_snapshot, 'lineno')
            # print(f"--- Iteration {i} ---")
            # for stat in top_stats[:1]:
            #     print(stat)
            
            # Check wrapper.chunks size
            if hasattr(wrapper, 'chunks'):
                print(f"Iteration {i}: wrapper.chunks size: {len(wrapper.chunks)}")
            if hasattr(wrapper, 'chunk_buffer'):
                 print(f"Iteration {i}: wrapper.chunk_buffer size: {len(wrapper.chunk_buffer)}")

    print("Finished")
    tracemalloc.stop()

if __name__ == "__main__":
    # Test with logging disabled (Expectation: chunks size stays low)
    asyncio.run(run_test(disable_logging=True))
    
    # Test with logging enabled (Expectation: chunks size grows)
    asyncio.run(run_test(disable_logging=False))
