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

---

## 2026-01-18: Upstream 머지 충돌 위험 분석

### 개요

`pep-621` 브랜치에서 main 대비 변경한 파일들이 upstream 릴리즈 반영 시 충돌 가능성을 분석합니다.

### 변경된 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `pyproject.toml` | 수정 | PEP-621 섹션 추가 |
| `Makefile` | 수정 | UV 기반 타겟 추가 |
| `CUSTOMCHANGES.md` | 신규 | 변경 이력 문서 |
| `tests/*/__init__.py` (4개) | 신규 | pytest-xdist 병렬 테스트용 |

### 충돌 위험도 분석

#### 🔴 고위험: `pyproject.toml`

- **Upstream 변경 빈도**: 3개월간 **83회** 변경
- **충돌 원인**:
  - 버전 업데이트 (`version = "X.X.X"`)
  - 새로운 의존성 추가/업데이트
  - optional-dependencies 변경
- **영향 범위**: 파일 상단(`[project]`)과 중간(`[project.optional-dependencies]`) 모두 영향

**권장 대응**:
```bash
# 머지 전 upstream 변경사항 확인
git diff upstream/main -- pyproject.toml

# 충돌 발생 시 전략
# 1. [project] 섹션의 version → upstream 값 사용
# 2. dependencies/optional-dependencies → upstream 값 우선, 커스텀 추가분 확인
# 3. [tool.poetry.*] 섹션 → Poetry 설정은 upstream 따름
```

#### 🟢 저위험: `Makefile`

- **Upstream 변경 빈도**: 3개월간 **4회** 변경
- **충돌 가능성**: 낮음 (새로운 타겟만 추가, 기존 타겟 미수정)
- **이유**: UV 기반 타겟은 파일 끝에 추가되어 기존 타겟과 분리됨

**권장 대응**: 대부분 자동 머지 가능. 충돌 시 양쪽 변경 모두 보존.

#### 🟢 저위험: `tests/*/__init__.py` 파일들

- **충돌 가능성**: 거의 없음
- **이유**: 빈 `__init__.py` 파일, upstream에서 동일 파일 추가 가능성 낮음

#### ⚪ 무위험: `CUSTOMCHANGES.md`

- **충돌 가능성**: 없음
- **이유**: 커스텀 전용 파일, upstream에 존재하지 않음

### 권장 머지 전략

1. **자동화 스크립트 고려**:
   ```bash
   # pyproject.toml 버전 자동 동기화 예시
   UPSTREAM_VERSION=$(grep '^version = ' upstream_pyproject.toml | head -1)
   sed -i "s/^version = .*/version = ${UPSTREAM_VERSION}/" pyproject.toml
   ```

2. **머지 순서**:
   1. `CUSTOMCHANGES.md` 제외하고 머지
   2. `pyproject.toml` 충돌 해결 (가장 복잡)
   3. 나머지 파일 자동 머지

3. **테스트 확인**:
   ```bash
   make test-unit-uv  # 머지 후 테스트 실행
   ```


### 장기적 권장사항

| 권장 | 설명 |
|------|------|
| PEP-621 Upstream 제안 | LiteLLM 메인 저장소에 PEP-621 지원 PR 제출 고려 |
| 버전 동기화 자동화 | CI에서 버전 충돌 자동 해결 스크립트 추가 |
| 변경 최소화 | 기존 Poetry 섹션 수정은 피하고 추가만 함 |

---

## 2026-01-18: Poetry → PEP-621 동기화 스크립트 추가

### 변경 목적
- Upstream 머지 후 Poetry 의존성을 PEP-621 형식으로 자동 동기화
- 수동 동기화 작업 제거

### 추가된 파일
- `scripts/sync_poetry_to_pep621.py`

### 동기화 대상

| Poetry 소스 | PEP-621 타겟 |
|------------|-------------|
| `[tool.poetry]` version | `[project]` version |
| `[tool.poetry.dependencies]` | `[project.dependencies]` |
| `[tool.poetry.group.dev.dependencies]` | `[project.optional-dependencies].dev` |
| `[tool.poetry.group.proxy-dev.dependencies]` | `[project.optional-dependencies].proxy-dev` |
| `[tool.poetry.extras].proxy` | `[project.optional-dependencies].proxy` |
| `[tool.poetry.extras].extra_proxy` | `[project.optional-dependencies].extra_proxy` |
| `[tool.poetry.extras].utils` | `[project.optional-dependencies].utils` |
| `[tool.poetry.extras].caching` | `[project.optional-dependencies].caching` |
| `[tool.poetry.extras].semantic-router` | `[project.optional-dependencies].semantic-router` |
| `[tool.poetry.extras].mlflow` | `[project.optional-dependencies].mlflow` |

### 버전 변환 규칙

| Poetry 형식 | PEP-517 결과 | 설명 |
|------------|-------------|------|
| `^1.2.3` | `>=1.2.3,<2.0.0` | Caret (major 변경 금지) |
| `^0.2.3` | `>=0.2.3,<0.3.0` | Caret (0.x는 minor 변경 금지) |
| `~1.2.3` | `>=1.2.3,<1.3.0` | Tilde (minor 변경 금지) |
| `1.2.3` | `==1.2.3` | Bare version |
| `*` | (제약 없음) | Any version |
| `>=1.0,<2.0` | `>=1.0,<2.0` | 이미 PEP-517 형식 |

### 환경 마커 변환

| Poetry 형식 | PEP-517 결과 |
|------------|-------------|
| `python = ">=3.9"` | `; python_version >= '3.9'` |
| `python = ">=3.9,<3.14"` | `; python_version >= '3.9' and python_version < '3.14'` |
| `markers = "sys_platform != 'win32'"` | `; sys_platform != 'win32'` |

### 기능

| 기능 | 설명 |
|------|------|
| 버전 변환 | Poetry 버전 표기법을 PEP-517 형식으로 자동 변환 |
| 마커 변환 | python/markers 조건을 PEP-517 환경 마커로 변환 |
| 포맷 유지 | 큰따옴표(`"`) 스타일 유지 |
| `--dry-run` | 변경 미리보기 (파일 수정 안 함) |
| `--check` | 동기화 상태 확인 (CI용, 불일치 시 exit 1) |

### Makefile 타겟

```bash
make sync-deps          # 동기화 실행
make sync-deps-check    # 동기화 상태 확인 (CI용)
make sync-deps-dry-run  # 변경 미리보기
```

### 사용법 (Upstream 머지 후)

```bash
git merge upstream/main
make sync-deps           # Poetry → PEP-621 동기화
make test-unit-uv        # 테스트 실행
```

