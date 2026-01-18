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
