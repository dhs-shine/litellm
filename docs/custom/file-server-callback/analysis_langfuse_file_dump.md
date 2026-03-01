# Langfuse 파일 덤프 분석 리포트

## 1. 기존 파일 덤프 콜백이 존재하는가?

**로컬 파일 시스템에 직접 write하는 콜백은 존재하지 않습니다.** 하지만 유사한 패턴의 콜백들이 존재합니다:

| 콜백 | 저장 대상 | 사용하는 JSON 형식 |
|------|----------|-------------------|
| [s3.py](file:///Users/dhsshin/Documents/LLMOps/litellm/litellm/integrations/s3.py) | AWS S3 | `StandardLoggingPayload` |
| [gcs_bucket.py](file:///Users/dhsshin/Documents/LLMOps/litellm/litellm/integrations/gcs_bucket/gcs_bucket.py) | Google Cloud Storage | `StandardLoggingPayload` |
| [langfuse.py](file:///Users/dhsshin/Documents/LLMOps/litellm/litellm/integrations/langfuse/langfuse.py) | Langfuse API | **독자적인 trace/generation 구조** |

## 2. Langfuse JSON vs StandardLoggingPayload — 핵심 차이

> [!IMPORTANT]
> Langfuse가 구성하는 JSON과 `StandardLoggingPayload`는 **완전히 다른 구조**입니다.

### `StandardLoggingPayload` (S3/GCS가 사용)
```json
{
  "id": "...",
  "trace_id": "...",
  "call_type": "completion",
  "model": "gpt-4",
  "prompt_tokens": 100,
  "completion_tokens": 50,
  "response_cost": 0.015,
  "messages": [...],
  "response": {...},
  "metadata": {...},
  "hidden_params": {...}
}
```
- LiteLLM의 **표준 로깅 형식** — 모든 콜백에서 `kwargs["standard_logging_object"]`로 접근 가능
- **이미 구성되어 있으므로 추가 CPU 비용 없음**

### Langfuse 형식
```json
{
  "trace": {
    "id": "...", "name": "litellm-completion",
    "session_id": "...", "user_id": "...",
    "input": {"messages": [...]}, "output": "...",
    "tags": [...]
  },
  "generation": {
    "name": "...", "model": "gpt-4",
    "model_parameters": {...},
    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    "usage_details": {"cache_creation_input_tokens": 0, ...}
  }
}
```
- Langfuse **전용** 구조 (trace → generation 계층)
- metadata 정제, 태그 구성, masking 등 Langfuse-specific 변환 로직 포함
- 이 JSON은 Langfuse SDK의 `trace()` / `generation()` 메서드에 분산되어 전달됨 — **하나의 JSON object로 합쳐진 형태가 없음**

## 3. 세 가지 접근법 비교

### 옵션 A: Langfuse 콜백 위에 파일 덤프 기능 확장

| 장점 | 단점 |
|------|------|
| Langfuse trace/generation 구조를 그대로 재사용 | Langfuse 코드가 복잡해짐 (SRP 위반) |
| CPU 중복 없음 | Langfuse 없이 파일 덤프만 하고 싶을 때 불가 |
| | Langfuse SDK 의존성이 필수 |
| | upstream 업데이트 시 merge conflict 위험 |

> [!WARNING]
> Langfuse 콜백의 `_log_langfuse_v2` 메서드는 Langfuse SDK의 `trace()`, `generation()` 객체를 직접 호출합니다. 이 과정에서 JSON이 "하나의 dict"로 모이는 지점이 없기 때문에, 파일에 쓰려면 `trace_params`와 `generation_params`를 별도로 캡처해서 합쳐야 합니다. 이 자체가 상당한 코드 수정을 요구합니다.

### 옵션 B: 별도의 파일 덤프 콜백 (StandardLoggingPayload 기반) ⭐ **추천**

| 장점 | 단점 |
|------|------|
| Langfuse와 독립적 enable/disable | Langfuse 고유의 trace 계층 구조가 아닌 StandardLoggingPayload 형식으로 저장 |
| `StandardLoggingPayload`는 이미 구성되어 있으므로 **추가 CPU 비용 거의 없음** | |
| S3/GCS 로거와 동일 패턴으로 구현 가능 (검증된 패턴) | |
| 코드 100줄 미만으로 구현 가능 | |
| upstream litellm 업데이트와 충돌 없음 | |

> [!TIP]
> **CPU 효율성 우려는 불필요합니다.** `StandardLoggingPayload`는 LiteLLM 로깅 파이프라인에서 **모든 콜백 호출 전에 이미 구성됩니다** (`kwargs["standard_logging_object"]`). 별도의 콜백에서 이 객체를 직렬화(`json.dumps`)하는 비용은 무시할 수 있는 수준입니다. Langfuse가 하는 "JSON 구성"은 Langfuse trace 구조로의 **변환** 작업이지, `StandardLoggingPayload` 자체를 중복 생성하는 것이 아닙니다.

### 옵션 C: Langfuse 콜백을 wrapping하는 별도 콜백

Langfuse `log_event_on_langfuse`의 리턴 값을 캡처해서 파일에 쓰는 방식. 하지만 이 함수는 `{"trace_id": ..., "generation_id": ...}`만 반환하므로 실제 JSON 데이터를 얻을 수 없어 **실용적이지 않습니다.**


## 4. 결론 및 추천

### 추천: **옵션 B — 별도의 `LocalFileDumpLogger` 콜백**

**근거:**

1. **CPU 효율성 문제가 없다**: `StandardLoggingPayload`는 이미 구성된 객체이므로 "이중으로 JSON을 구성"하는 것이 아닙니다. 추가 비용은 `json.dumps()` 직렬화 한 번뿐입니다.

2. **구현이 단순하다**: [s3.py](file:///Users/dhsshin/Documents/LLMOps/litellm/litellm/integrations/s3.py)를 거의 그대로 참조하여, `s3_client.put_object()` 대신 `open(filepath, 'w').write()`로 대체하면 됩니다.

3. **운영 유연성**: Langfuse와 독립적으로 on/off 가능.

4. **형식 호환성**: 만약 Langfuse의 trace/generation 구조가 필요한 게 아닌, 호출 데이터(model, tokens, messages, response, cost 등)를 JSON으로 남기는 것이 목적이라면 `StandardLoggingPayload`가 **더 범용적이고 풍부한 정보**(40+ fields)를 담고 있습니다.

### 구현 참고 (S3Logger 패턴 기반)

```python
class LocalFileDumpLogger:
    def __init__(self, output_dir: str = "./litellm_logs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def log_event(self, kwargs, response_obj, start_time, end_time, print_verbose):
        payload = kwargs.get("standard_logging_object", None)
        if payload is None:
            return
        
        date_dir = os.path.join(self.output_dir, start_time.strftime("%Y-%m-%d"))
        os.makedirs(date_dir, exist_ok=True)
        
        filename = f"{payload['id']}.json"
        filepath = os.path.join(date_dir, filename)
        
        from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
        with open(filepath, 'w') as f:
            f.write(safe_dumps(payload))
```

> [!NOTE]
> 만약 "Langfuse에 보내는 것과 동일한 JSON"이 **반드시** 필요한 경우(예: Langfuse의 trace 구조를 오프라인에서 재현해야 하는 경우), 옵션 A가 필요할 수 있습니다. 하지만 이 경우에도 Langfuse 코드를 직접 수정하기보다는 Langfuse의 `_log_langfuse_v2` 메서드에서 `trace_params`와 `generation_params`를 hook하는 방식이 더 안전합니다. 이 경우의 구체적인 구현 방향도 논의할 수 있습니다.
