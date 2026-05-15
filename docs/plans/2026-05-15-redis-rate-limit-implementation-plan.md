# Redis Rate Limit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** API rate limit 저장소를 Redis로 선택할 수 있게 하여 여러 API 인스턴스에서 동일한 제한 정책을 공유합니다.

**Architecture:** 기존 rate limit 미들웨어는 유지하되 저장소 인터페이스를 `memory`와 `redis` 구현으로 분리합니다. Redis 구현은 sorted set과 Lua script를 사용해 sliding window 카운터를 원자적으로 갱신하고, API Key 원문은 SHA-256 해시로 변환해 Redis key에 저장합니다.

**Tech Stack:** FastAPI, Starlette Middleware, redis-py, Redis Lua script, pytest

---

### Task 1: 설정 테스트 추가

**Files:**
- Modify: `backend/tests/test_bootstrap.py`

**Step 1: Write the failing test**

`rate_limit_backend`, `rate_limit_redis_prefix`, `rate_limit_fail_open` 기본값과 환경 변수 override 테스트를 추가합니다.

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\test_bootstrap.py -q`

Expected: `Settings`에 새 필드가 없어 실패합니다.

**Step 3: Write minimal implementation**

`backend/app/core/config.py`에 새 설정 필드를 추가합니다.

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\test_bootstrap.py -q`

Expected: PASS

### Task 2: Redis 저장소 단위 테스트 추가

**Files:**
- Modify: `backend/tests/middleware/test_rate_limit.py`

**Step 1: Write the failing test**

Redis 저장소가 Lua script를 통해 허용/차단 결정을 만들고, Redis key에 API Key 원문을 노출하지 않는 테스트를 추가합니다.

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\middleware\test_rate_limit.py -q`

Expected: Redis 저장소 클래스가 없어 실패합니다.

**Step 3: Write minimal implementation**

`backend/app/middleware/rate_limit.py`에 `InMemoryRateLimitStore`, `RedisRateLimitStore`, `create_rate_limit_store`를 추가합니다.

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\middleware\test_rate_limit.py -q`

Expected: PASS

### Task 3: 미들웨어 Redis backend 연결 테스트

**Files:**
- Modify: `backend/tests/middleware/test_rate_limit.py`

**Step 1: Write the failing test**

`RATE_LIMIT_BACKEND=redis`이면 미들웨어가 Redis 저장소 factory를 사용하고, Redis 장애 시 fail-open이면 요청을 통과시키는 테스트를 추가합니다.

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\middleware\test_rate_limit.py -q`

Expected: backend 선택과 fail-open 처리가 없어 실패합니다.

**Step 3: Write minimal implementation**

미들웨어가 store factory를 통해 저장소를 만들고, Redis 저장소 장애 시 `RATE_LIMIT_FAIL_OPEN=true`이면 요청을 통과시키게 합니다.

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest backend\tests\middleware\test_rate_limit.py -q`

Expected: PASS

### Task 4: 운영 상태 API 반영

**Files:**
- Modify: `backend/app/admin/operations.py`
- Modify: `backend/tests/admin/test_operations_router.py`
- Modify: `frontend/src/lib/operations-api.ts`
- Modify: `frontend/src/features/operations/OperationsStatusWorkspace.tsx`
- Modify: `frontend/src/features/operations/OperationsStatusWorkspace.test.tsx`

**Step 1: Write the failing test**

운영 상태 응답과 화면에 `rate_limit.backend`, `rate_limit.fail_open`이 표시되는 테스트를 추가합니다.

**Step 2: Run test to verify it fails**

Run:
- `.venv\Scripts\python.exe -m pytest backend\tests\admin\test_operations_router.py -q`
- `npm test -- OperationsStatusWorkspace.test.tsx`

Expected: 새 필드가 없어 실패합니다.

**Step 3: Write minimal implementation**

백엔드 응답 모델과 프론트 타입/화면을 새 필드에 맞춰 갱신합니다.

**Step 4: Run test to verify it passes**

Run:
- `.venv\Scripts\python.exe -m pytest backend\tests\admin\test_operations_router.py -q`
- `npm test -- OperationsStatusWorkspace.test.tsx`

Expected: PASS

### Task 5: 실행 설정과 문서 반영

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `.env.example`
- Modify: `infra/compose/docker-compose.yml`
- Modify: `README.md`

**Step 1: Update runtime configuration**

`redis` Python dependency를 추가하고, Compose API 환경 변수에 `RATE_LIMIT_BACKEND=redis`를 명시합니다.

**Step 2: Update docs**

README에 Redis 기반 분산 rate limit 동작과 fail-open 정책을 설명합니다.

**Step 3: Run full verification**

Run:
- `.venv\Scripts\python.exe -m pytest backend\tests -q`
- `npm test`
- `npm run build`
- `docker compose -f infra\compose\docker-compose.yml config`
- `git diff --check origin/develop..HEAD`

Expected: 모두 성공합니다.
