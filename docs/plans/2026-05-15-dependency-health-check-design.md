# 외부 의존성 상태 점검 설계

## 목표

DocSearch AI가 운영 환경에서 PostgreSQL, Qdrant, MinIO, vLLM 같은 외부 의존성 연결 상태를 `/ready` 응답에 포함하도록 확장합니다. 개발 환경에서는 기본적으로 기존처럼 설정 점검만 수행하고, 필요할 때 환경 변수로 외부 점검을 켤 수 있게 합니다.

## 포함 범위

- `/ready` 응답에 외부 의존성 점검 결과를 포함할 수 있게 합니다.
- `DEPENDENCY_HEALTH_CHECKS_ENABLED`로 외부 점검 실행 여부를 제어합니다.
- 운영 환경(`APP_ENV=production`)에서는 기본적으로 외부 점검을 활성화합니다.
- 설정 점검이 실패하면 외부 연결 시도를 건너뛰어 불필요한 대기와 잡음을 줄입니다.
- PostgreSQL, Qdrant, MinIO, vLLM 상태를 점검합니다.
- Redis 큐와 BGE Reranker는 해당 백엔드가 활성화된 경우에만 점검합니다.
- 각 의존성은 독립적으로 `ready` 또는 `not_ready` 결과를 반환합니다.

## 제외 범위

- 프론트엔드 관리자 대시보드 상태 표시
- Prometheus 메트릭
- 재시도/서킷브레이커
- Kubernetes readiness/liveness probe 템플릿
- 실제 Redis 큐 구현

## 점검 정책

- `postgres`: 문서 메타데이터 또는 감사 로그 저장소가 PostgreSQL을 사용할 때 `SELECT 1`로 확인합니다.
- `qdrant`: Qdrant HTTP 상태 엔드포인트를 호출합니다.
- `minio`: MinIO live health 엔드포인트를 호출합니다.
- `vllm`: OpenAI 호환 `/models` 엔드포인트를 호출합니다.
- `redis`: `INDEXING_QUEUE_BACKEND=redis`일 때 Redis `PING`으로 확인합니다.
- `reranker`: `RERANKER_BACKEND=bge`일 때 리랭커 `/models` 엔드포인트를 호출합니다.

## 응답 예시

```json
{
  "status": "not_ready",
  "service": "docsearch-ai",
  "checks": [
    {
      "name": "configuration",
      "status": "ready",
      "message": "운영 설정 기준을 통과했습니다."
    },
    {
      "name": "qdrant",
      "status": "not_ready",
      "message": "Qdrant 연결에 실패했습니다: connection refused"
    }
  ]
}
```

## 후속 단계

다음 PR에서는 관리자 화면에서 역할에 따라 감사 로그 메뉴와 운영 상태 정보를 분리해 보여주는 작업을 진행합니다.
