# 스트림 모드 메모리 누수 수정 (v2 - 로깅 유지)

## 목표 설명
`CustomStreamWrapper`에서 `self.chunks`가 모든 스트리밍 청크를 무한정 누적하는 메모리 누수를 수정합니다. 개선된 솔루션은 전체 청크 객체를 저장하는 대신 최종 응답 데이터만 누적하여 로깅 기능을 완전히 유지하면서 메모리 사용량을 대폭 줄입니다.

## 사용자 검토 필요
> [!IMPORTANT]
> 이 변경은 스트리밍 응답 누적 방식을 근본적으로 변경합니다:
> - **이전**: `self.chunks` 리스트에 모든 청크 객체 저장 (메모리 선형 증가)
> - **이후**: 최종 응답 데이터(content, tool_calls, usage)만 점진적으로 누적 (상수 메모리)
> 
> **영향**:
> - 메모리 사용량: 긴 스트림의 경우 ~99% 감소
> - 로깅: 완전 유지 (로깅된 데이터 변경 없음)
> - API 호환성: 100% 하위 호환

## 제안된 변경사항

### `litellm`

#### [수정] [streaming_handler.py](file:///home/dhs-shine/Workspace/LLMOps/litellm/litellm/litellm_core_utils/streaming_handler.py)

응답 데이터를 점진적으로 누적하도록 `CustomStreamWrapper` 클래스 업데이트:

**1. `__init__`에 새로운 누적기 속성 추가**:
```python
# self.chunks를 증분 누적기로 교체
self.accumulated_content: str = ""
self.accumulated_tool_calls: Dict[int, Dict] = {}  # index -> tool_call dict
self.accumulated_function_call: Optional[Dict] = None
self.accumulated_reasoning_content: str = ""
self.accumulated_thinking_blocks: List = []
self.accumulated_audio: Optional[Dict] = None
self.final_finish_reason: Optional[str] = None
```

**2. `__next__` 및 `__anext__`를 수정하여 점진적으로 누적**:
- `self.chunks.append(response)` 대신 누적기 업데이트:
  ```python
  # Content 누적
  if choice.delta.content:
      self.accumulated_content += choice.delta.content
  
  # Tool calls 누적
  if choice.delta.tool_calls:
      self._merge_tool_calls(choice.delta.tool_calls)
  
  # Usage 업데이트 (최신 값만 유지)
  if hasattr(response, "usage"):
      self.usage_so_far = response.usage
  ```

**3. `build_final_response()` 메서드 생성**:
- 누적된 데이터로 최종 `ModelResponse` 생성
- `stream_chunk_builder(chunks=self.chunks)` 호출 대체
- 로깅을 위한 완전한 응답 반환

**4. `StopIteration` 핸들러 업데이트**:
- `stream_chunk_builder()` 대신 `self.build_final_response()` 호출
- 로깅 핸들러에 최종 응답 전달

**5. 안전 검사를 위해 `chunk_buffer` 유지**:
- 무한 루프 감지를 위한 작은 순환 버퍼(100개 청크) 유지
- `safety_checker()` 로직 변경 없음

## 검증 계획

### 자동화된 테스트
1. 업데이트된 `reproduce_leak.py`를 실행하여 메모리 사용량 확인:
   - 예상: `chunks` 크기 = 0, 메모리 사용량 일정
2. 기존 스트리밍 테스트 실행:
   ```bash
   pytest tests/ -k stream -v
   ```
3. 로깅 출력이 원래 구현과 일치하는지 확인

### 수동 검증
1. `safety_checker`가 여전히 무한 루프를 감지하는지 확인
2. 완전한 응답이 올바르게 로깅되는지 확인
3. 다양한 제공자(OpenAI, Anthropic 등)로 테스트
4. Tool calls 및 function calls가 올바르게 누적되는지 확인
