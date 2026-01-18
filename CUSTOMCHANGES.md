# Custom Changes

이 문서는 upstream LiteLLM 저장소에서 로컬로 적용한 변경 사항을 기록합니다.

## 2026-01-18: PEP-621 표준 준수로 pyproject.toml 변환

### 변경 목적
- `uv` 패키지 매니저 지원을 위해 `pyproject.toml`을 PEP-621 표준으로 변환
- 기존 Poetry 호환성 유지

### 변경 내용

#### 1. `[project]` 섹션 추가 (PEP-621 표준)
```toml
[project]
name = "litellm"
version = "1.80.17"
requires-python = ">=3.9,<4.0"
dependencies = [...]
```

#### 2. 빌드 시스템 변경
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

#### 3. `[project.optional-dependencies]` 추가
Poetry의 `[tool.poetry.group.*.dependencies]`를 PEP-621 표준으로 변환:
- `dev`: 개발 도구 (pytest, black, mypy, ruff 등)
- `proxy-dev`: 프록시 개발 의존성 (prisma, hypercorn 등)
- `proxy`, `extra_proxy`, `utils`, `caching`, `semantic-router`, `mlflow`: 기존 extras 유지

#### 4. Poetry 설정 유지
`[tool.poetry.*]` 섹션은 하위 호환성을 위해 그대로 유지

### 사용법

```bash
# uv 사용
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"           # 개발 의존성
uv pip install -e ".[proxy,dev]"     # proxy + 개발

# poetry 사용 (기존 방식)
poetry install --with dev
poetry install --with dev,proxy-dev
```

### 영향받는 파일
- `pyproject.toml`

---

## 2026-01-18: Makefile에 UV 기반 타겟 추가

### 변경 목적
- `poetry` 없이 `uv`만으로도 개발 작업 가능하도록 Makefile 확장
- 기존 Poetry 기반 타겟은 그대로 유지 (하이브리드 방식)

### 추가된 타겟

| 타겟 | 설명 |
|------|------|
| `install-dev-uv` | uv로 개발 의존성 설치 |
| `install-proxy-dev-uv` | uv로 proxy 개발 의존성 설치 |
| `install-test-deps-uv` | uv로 테스트 의존성 설치 |
| `format-uv` | Black 포맷팅 적용 (uv) |
| `format-check-uv` | Black 포맷팅 검사 (uv) |
| `lint-uv` | 전체 린팅 (uv) |
| `lint-ruff-uv` | Ruff 린트 (uv) |
| `lint-mypy-uv` | MyPy 타입 체크 (uv) |
| `check-circular-imports-uv` | 순환 import 검사 (uv) |
| `check-import-safety-uv` | import 안전성 검사 (uv) |
| `test-uv` | 전체 테스트 (uv) |
| `test-unit-uv` | 단위 테스트 (uv) |
| `test-integration-uv` | 통합 테스트 (uv) |

### 사용법

```bash
# uv 설치 후
make install-dev-uv       # 개발 환경 설정
make lint-uv              # 린팅
make test-unit-uv         # 단위 테스트
```

### 영향받는 파일
- `Makefile`

---

## 2026-01-18: pytest-xdist 병렬 테스트 충돌 해결

### 변경 목적
- `pytest -n 4` 병렬 테스트 시 동일한 파일명(`test_handler.py`)으로 인한 import 충돌 해결
- `import file mismatch` 에러 방지

### 원인
pytest-xdist가 병렬 실행할 때 동일한 이름의 테스트 파일이 여러 디렉토리에 있으면 모듈 충돌 발생

### 해결 방법
충돌하는 `test_handler.py` 파일이 있는 디렉토리에 `__init__.py` 추가

### 추가된 파일
```
tests/test_litellm/integrations/__init__.py
tests/test_litellm/integrations/websearch_interception/__init__.py
tests/test_litellm/llms/huggingface/embedding/__init__.py
tests/test_litellm/llms/openai/chat/guardrail_translation/__init__.py
```

### 검증 결과
```
168 passed, 5 skipped in 56.27s
```

---

## 2026-01-18: 코드 품질 도구 분석 (Black, Ruff, MyPy, Lint)

### 개요

LiteLLM 프로젝트에서 사용하는 코드 품질 도구들의 목적과 차이점을 정리합니다.

### 도구별 목적

| 도구 | 분류 | 주요 역할 | 자동 수정 |
|------|------|-----------|-----------|
| **Black** | Formatter | 코드 스타일 통일 | ✅ |
| **Ruff** | Linter | 코드 품질/버그 탐지 | ⚠️ 일부 |
| **MyPy** | Type Checker | 타입 오류 검출 | ❌ |
| **Lint** | 개념/프로세스 | 품질 검사 전반 | - |

### 도구 상세

#### Black (코드 포매터)
- Python 코드의 형식을 자동으로 정리하는 **opinionated formatter**
- 들여쓰기, 줄 바꿈, 따옴표 스타일, 공백 등을 통일된 규칙으로 변환
- "하나의 올바른 방법"을 강제하여 스타일 논쟁을 없앰

#### Ruff (린터)
- Rust로 작성된 초고속 Python 린터
- Flake8, isort, pyupgrade 등의 규칙을 통합
- 미사용 import, 정의되지 않은 변수, 코드 복잡도 등 검사
- 최신 버전은 포매팅 기능도 지원 (Black 대체 가능)

#### MyPy (타입 체커)
- Python 타입 힌트를 분석하여 타입 불일치 검출
- 함수 인자, 반환값, 변수의 타입 일관성 확인
- 런타임이 아닌 **정적 분석** 단계에서 오류를 잡아냄

### LiteLLM 프로젝트 설정

#### 현재 전략: 역할 분리
```toml
# pyproject.toml
black = "^23.12.0"   # 포매팅 전용
ruff = "^0.1.0"      # 린팅 전용

[tool.isort]
profile = "black"    # isort를 Black과 호환되게 설정
```

#### Makefile 명령어
```bash
make format      # Black 포매팅 적용
make lint        # 전체 린트 (Ruff + MyPy + Black check)
make lint-ruff   # Ruff만 실행
make lint-mypy   # MyPy만 실행
```

### Black과 Ruff 충돌 방지

현재 프로젝트는 **역할 분리 방식**을 채택:
- Ruff: 린팅 용도 (`ruff check`)
- Black: 포매팅 용도 (`black .`)

이 방식으로 두 도구 간 충돌을 방지하고 있음.

> **향후 고려사항**: Ruff v0.1+ 이후 `ruff format` 지원으로 Black을 완전히 대체 가능. 
> 프로젝트 통일성을 위해 Ruff 단일 도구로 전환 검토 가능.

