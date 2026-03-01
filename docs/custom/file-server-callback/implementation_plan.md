# File Server Callback 구현 계획

LiteLLM의 `CustomLogger`를 상속하여, LLM 호출 완료 시 `StandardLoggingPayload`를 rust-file-server API(`POST /v1/files`)로 전송하는 콜백을 구현한다.

## Proposed Changes

### File Server Logger 모듈

#### [NEW] [__init__.py](file:///Users/dhsshin/Documents/LLMOps/litellm/litellm/integrations/file_server/__init__.py)

빈 init 파일.

---

#### [NEW] [file_server_logger.py](file:///Users/dhsshin/Documents/LLMOps/litellm/litellm/integrations/file_server/file_server_logger.py)

`CustomLogger`를 상속하는 `FileServerLogger` 클래스:

| 항목 | 설계 |
|------|------|
| **Base class** | `CustomLogger` (배치 불필요, 건별 전송) |
| **HTTP client** | `httpx.AsyncClient` (connection pooling, keepalive) |
| **전송 데이터** | `kwargs["standard_logging_object"]` (`StandardLoggingPayload`) |
| **전송 방식** | 건별 전송 (`mode: "async"`) — 데이터 유실 방지 |
| **호출 지점** | `async_log_success_event` + `async_log_failure_event` |
| **파일 경로** | `{YYYY-MM-DD}/{payload_id}.json` (S3Logger와 동일 패턴) |

환경변수:

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `FILE_SERVER_URL` | (필수) | rust-file-server 베이스 URL (예: `http://rust-file-server:8080`) |
| `FILE_SERVER_AUTH_TOKEN` | (필수) | Bearer 토큰 |
| `FILE_SERVER_PATH_PREFIX` | `""` | 파일 경로 prefix (예: `litellm-logs/`) |
| `FILE_SERVER_WRITE_MODE` | `"async"` | rust-file-server의 write mode (`async`/`sync`) |
| `FILE_SERVER_TIMEOUT` | `5` | HTTP 요청 타임아웃 (초) |

핵심 로직 (pseudo):
```python
class FileServerLogger(CustomLogger):
    def __init__(self):
        self.client = httpx.AsyncClient(...)
        # read env vars

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        payload = kwargs.get("standard_logging_object")
        if payload is None:
            return
        file_path = f"{self.path_prefix}{start_time.strftime('%Y-%m-%d')}/{payload['id']}.json"
        await self.client.post(f"{self.base_url}/v1/files", json={
            "path": file_path,
            "content": payload,
            "mode": self.write_mode,
        }, headers={"Authorization": f"Bearer {self.auth_token}"})

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        # 동일 로직 (에러 페이로드도 저장)
```

---

### 테스트

#### [NEW] [test_file_server_logger.py](file:///Users/dhsshin/Documents/LLMOps/litellm/tests/test_litellm/integrations/test_file_server_logger.py)

`httpx` 호출을 mock하여 검증하는 유닛 테스트:

1. **`test_async_log_success_sends_payload`** — success 이벤트 시 올바른 URL/body/header로 POST 호출 확인
2. **`test_async_log_failure_sends_payload`** — failure 이벤트도 동일하게 전송 확인
3. **`test_no_payload_skips_request`** — `standard_logging_object`가 None이면 HTTP 호출 안 함
4. **`test_file_path_format`** — 날짜/ID 기반 경로 생성 확인
5. **`test_path_prefix_applied`** — prefix 설정 시 경로에 반영
6. **`test_http_error_does_not_raise`** — API 오류 시 예외를 삼켜서 LiteLLM 동작에 영향 없음

## Verification Plan

### Automated Tests

```bash
poetry run pytest tests/test_litellm/integrations/test_file_server_logger.py -v
```

### 기존 테스트 비파괴 확인

```bash
make test-unit
```

> [!NOTE]
> 새 모듈을 추가하는 것이므로 기존 코드를 수정하지 않습니다. 기존 테스트에 영향이 없을 것으로 예상되지만, `make test-unit`으로 확인합니다.
