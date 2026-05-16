# 테스트 및 성능 기준표

이 문서는 DocSearch AI V2 MVP를 리뷰하거나 데모하기 전에 확인할 테스트 기준과 로컬 성능 측정 기준을 정리합니다. V1은 `main` 브랜치에 보존된 프로토타입이고, 아래 자동 검증 기준은 `develop` 브랜치의 V2 아키텍처를 대상으로 합니다.

## 자동 검증 기준

2026-05-16 기준 `develop`에서 PR 생성 전 기본으로 확인할 명령입니다.

| 영역 | 명령 | 현재 기준 | 합격 기준 |
| --- | --- | --- | --- |
| Backend test | `.venv\Scripts\python.exe -m pytest backend\tests -q` | 140 passed | 실패 없음 |
| Frontend test | `npm.cmd run test` in `frontend` | 40 passed | 실패 없음 |
| Frontend build | `npm.cmd run build` in `frontend` | build passed | TypeScript/Vite build 성공 |
| Compose config | `docker compose -f infra\compose\docker-compose.yml config` | 수동 실행 | 설정 파싱 성공 |
| Notebook compose | `docker compose -f infra\compose\docker-compose.yml -f infra\compose\docker-compose.notebook.yml config` | 수동 실행 | 설정 파싱 성공 |

Vite가 500 kB 이상 chunk 경고를 출력할 수 있습니다. 현재는 Ant Design 중심 번들 크기 경고로 보고, build 실패로 보지 않습니다.

## 로컬 실행 프로필

| 프로필 | 명령 | 용도 | 검증 제외 |
| --- | --- | --- | --- |
| 기본 Compose | `docker compose -f infra\compose\docker-compose.yml up --build` | 전체 서비스 경계 확인 | GPU가 없으면 vLLM 컨테이너 단계에서 막힐 수 있음 |
| 노트북 Compose | `docker compose -f infra\compose\docker-compose.yml -f infra\compose\docker-compose.notebook.yml up --build` | Galaxy Book6 Pro 같은 로컬 노트북 검증 | 실제 vLLM/BGE 품질과 GPU latency |
| 외부 모델 연결 | `LLM_BASE_URL`, `EMBEDDING_BASE_URL`, `RERANKER_BASE_URL`을 host 또는 별도 서버로 지정 | 로컬 GPU 또는 사내 GPU 서버 연결 | 서버별 VRAM, driver, 모델 설정 차이는 별도 기록 |

노트북 검증은 기능 흐름을 빠르게 확인하기 위한 기준입니다. 실제 운영 성능은 vLLM, BGE-M3, BGE reranker를 붙인 환경에서 별도로 측정합니다.

## 성능 측정 항목

| 항목 | 측정 대상 | 로컬 MVP 목표 | 측정 방법 |
| --- | --- | --- | --- |
| API 생존 응답 | `GET /health` | 200 ms 이하 | PowerShell `Measure-Command` |
| readiness | `GET /ready` | dependency check 비활성 500 ms 이하, 활성 시 timeout 설정 이하 | `DEPENDENCY_HEALTH_CHECKS_ENABLED`별 분리 측정 |
| 문서 업로드 응답 | `POST /v1/documents` | 작은 TXT 3초 이하 | 업로드 API 응답 시간 |
| 인덱싱 처리 시간 | 업로드 후 `indexing_status=completed`까지 | 노트북 stub 10초 이하 | 문서 목록 polling |
| 검색 latency | `POST /v1/search` | 1초 이하 | 같은 query 5회 반복 |
| 채팅 응답 시간 | `POST /v1/chat` | 노트북 stub 3초 이하, 실제 vLLM은 모델별 기록 | 같은 질문 3회 반복 |
| rate limit 검증 | `/v1/*` 요청 제한 | 초과 요청 429, `Retry-After` 반환 | 낮은 제한값으로 반복 호출 |
| 큐 backlog 확인 | `/v1/admin/operations`의 `indexing_queue.pending_jobs` | worker 동작 시 backlog 감소 | 문서 업로드 후 운영 화면 확인 |

## Windows PowerShell 측정 예시

아래 예시는 노트북 Compose 기준입니다. API Key는 기본 관리자 키인 `local-dev-key`를 사용합니다.

```powershell
$baseUrl = "http://localhost:8080/api"
$headers = @{ "X-API-Key" = "local-dev-key" }

Measure-Command {
  Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
}

Measure-Command {
  Invoke-RestMethod -Uri "$baseUrl/ready" -Method Get
}
```

문서 업로드:

```powershell
"DocSearch rate limit and indexing queue test document." |
  Set-Content -Encoding utf8 .\tmp-docsearch-test.txt

Measure-Command {
  curl.exe -sS `
    -H "X-API-Key: local-dev-key" `
    -F "file=@tmp-docsearch-test.txt;type=text/plain" `
    "$baseUrl/v1/documents"
}
```

검색:

```powershell
$searchBody = @{
  query = "indexing queue"
  limit = 5
} | ConvertTo-Json

1..5 | ForEach-Object {
  Measure-Command {
    Invoke-RestMethod `
      -Uri "$baseUrl/v1/search" `
      -Method Post `
      -Headers $headers `
      -ContentType "application/json" `
      -Body $searchBody
  }
}
```

채팅:

```powershell
$chatBody = @{
  question = "인덱싱 큐는 어떻게 확인하나요?"
  top_k = 5
} | ConvertTo-Json

1..3 | ForEach-Object {
  Measure-Command {
    Invoke-RestMethod `
      -Uri "$baseUrl/v1/chat" `
      -Method Post `
      -Headers $headers `
      -ContentType "application/json" `
      -Body $chatBody
  }
}
```

운영 상태와 큐 backlog:

```powershell
Invoke-RestMethod `
  -Uri "$baseUrl/v1/admin/operations" `
  -Method Get `
  -Headers $headers |
  Select-Object -ExpandProperty indexing_queue
```

## rate limit 검증 절차

Compose 환경에서 아래처럼 낮은 제한값을 적용한 뒤 같은 `/v1/*` 엔드포인트를 3회 이상 호출합니다.

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_BACKEND=redis
RATE_LIMIT_REQUESTS=2
RATE_LIMIT_WINDOW_SECONDS=60
```

합격 기준은 다음과 같습니다.

| 시나리오 | 기대 결과 |
| --- | --- |
| 제한 이내 요청 | HTTP 2xx 또는 해당 API의 정상 오류 |
| 제한 초과 요청 | HTTP 429 |
| 제한 초과 응답 헤더 | `Retry-After` 포함 |
| Redis 장애와 fail-open 활성 | 요청 통과, 운영 화면에서 Redis 상태 확인 |

## 결과 기록 양식

실측값은 장비와 모델에 따라 달라지므로 PR이나 포트폴리오 문서에는 아래 형식으로 환경과 함께 기록합니다.

| 날짜 | 환경 | Compose 프로필 | 모델 | 항목 | p50 | p95 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-16 | Galaxy Book6 Pro | notebook | local-dev-stub | 채팅 응답 | 측정 전 | 측정 전 | 기능 검증용 |

실제 vLLM/BGE 운영 성능표에는 GPU 모델, VRAM, vLLM 이미지 버전, `LLM_MODEL`, `EMBEDDING_MODEL`, `RERANKER_MODEL`, 문서 크기, 동시 요청 수를 함께 적습니다.
