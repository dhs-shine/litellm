# UV Support Changes Summary

이 문서는 프로젝트에 UV 패키지 매니저 지원을 추가하기 위해 수행한 변경 사항을 요약합니다.

## 변경 일자
2026-01-17

## 목적
Poetry 기반 프로젝트에서 UV도 함께 사용할 수 있도록 설정 추가

---

## 1. `pyproject.toml` 변경

### 1.1 PEP 621 `[project]` 섹션 추가

UV는 PEP 621 표준의 `[project]` 테이블이 필요합니다. 기존 `[tool.poetry]` 섹션은 그대로 유지하면서 `[project]` 섹션을 추가했습니다.

**추가된 섹션:**
- `[project]` - 기본 프로젝트 메타데이터
- `[project.optional-dependencies]` - extras 정의 (proxy, extra_proxy, dev, proxy-dev 등)
- `[project.scripts]` - CLI 엔트리포인트
- `[project.urls]` - 프로젝트 URL

### 1.2 Build Backend 변경

**변경 전:**
```toml
[build-system]
requires = ["poetry-core", "wheel"]
build-backend = "poetry.core.masonry.api"
```

**변경 후:**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["litellm"]
```

**이유:** Poetry의 build backend가 `grpcio` 의존성을 `>=1.62.3,<1.68.dev0 || >1.71.0` 형식으로 wheel metadata에 기록하는데, 이 `||` 구문은 PEP 508 표준이 아니라서 UV가 파싱하지 못했습니다. Hatchling은 PEP 621의 `[project]` 섹션을 사용하여 표준 형식으로 wheel을 빌드합니다.

---

## 2. 테스트 디렉토리 `__init__.py` 추가

pytest에서 같은 이름의 테스트 파일(`test_handler.py`)이 여러 디렉토리에 있을 때 모듈 충돌 문제가 발생했습니다.

**추가된 파일:**
- `tests/test_litellm/llms/huggingface/embedding/__init__.py`
- `tests/test_litellm/integrations/__init__.py`
- `tests/test_litellm/integrations/websearch_interception/__init__.py`

---

## 사용법

### Poetry (기존대로)
```bash
poetry install
poetry install -E proxy
poetry run pytest
```

### UV (새로 추가)
```bash
uv lock                    # lock 파일 생성
uv sync                    # 기본 의존성 설치
uv sync --extra proxy      # proxy extras 포함 설치
uv sync --extra dev        # 개발 의존성 포함 설치
uv run pytest              # 테스트 실행
```

---

## 생성된 파일

| 파일 | 설명 |
|------|------|
| `uv.lock` | UV용 lock 파일 (poetry.lock과 공존) |
| `tests/test_litellm/llms/huggingface/embedding/__init__.py` | pytest 모듈 충돌 해결 |
| `tests/test_litellm/integrations/__init__.py` | pytest 모듈 충돌 해결 |
| `tests/test_litellm/integrations/websearch_interception/__init__.py` | pytest 모듈 충돌 해결 |

---

## 호환성

- ✅ Poetry 사용자: 기존과 동일하게 `poetry install`, `poetry run` 사용 가능
- ✅ UV 사용자: `uv sync`, `uv run` 명령어 사용 가능
- ✅ pip 사용자: PEP 621 표준 준수로 `pip install .` 가능
