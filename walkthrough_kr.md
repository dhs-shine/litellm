# 스트림 모드 메모리 누수 수정

## 문제 (Problem)
스트리밍 모드에서 `CustomStreamWrapper`가 로깅을 위해 모든 스트리밍 청크를 `self.chunks`에 누적하고 있었습니다. 장시간 실행되는 스트림이나 처리량이 많은 애플리케이션의 경우, 이로 인해 메모리 사용량이 무제한으로 증가하여 메모리 누수가 발생했습니다.

## 해결책 (Solution)
`litellm.disable_streaming_logging` 설정에 따라 청크 저장 여부를 결정하도록 `CustomStreamWrapper`를 최적화했습니다.

- **`litellm.disable_streaming_logging = True`일 때**:
    - `self.chunks`에 데이터를 채우지 않습니다.
    - `safety_checker` (무한 루프 감지)를 위해 작은 크기(100개)의 `self.chunk_buffer`만 사용합니다.
    - 마지막에 전체 기록이 필요하지 않도록 사용량(Usage)을 점진적으로 계산하여 `self.usage_so_far`에 저장합니다.
    - 로깅을 위한 전체 응답 재구성을 건너뜁니다.

- **`litellm.disable_streaming_logging = False` (기본값)일 때**:
    - 기존 동작을 유지합니다 (로깅을 위해 전체 기록 저장).

## 검증 (Verification)
대규모 스트림(5000 청크)을 시뮬레이션하고 `self.chunks`의 크기를 측정하는 재현 스크립트 `reproduce_leak.py`를 생성했습니다.

### 결과 (Results)

| 시나리오 | `disable_streaming_logging` | `wrapper.chunks` 크기 | 메모리 동작 |
| :--- | :--- | :--- | :--- |
| **수정 적용** | `True` | **0** | 일정함 (낮음) |
| **기본값** | `False` | 5000 | 선형 증가 |

### 출력 로그 (Output Log)
```
Running test with disable_streaming_logging=True
Iteration 1000: wrapper.chunks size: 0
Iteration 1000: wrapper.chunk_buffer size: 100
...
Iteration 5000: wrapper.chunks size: 0
Iteration 5000: wrapper.chunk_buffer size: 100
Finished

Running test with disable_streaming_logging=False
Iteration 1000: wrapper.chunks size: 1000
Iteration 1000: wrapper.chunk_buffer size: 1000
...
Iteration 5000: wrapper.chunks size: 5000
Iteration 5000: wrapper.chunk_buffer size: 5000
```

## 사용 방법 (How to Use)
대용량 스트리밍 애플리케이션에서 메모리 누수를 방지하려면 다음과 같이 설정하세요:
```python
import litellm
litellm.disable_streaming_logging = True
```
