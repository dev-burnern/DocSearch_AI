# 운영 하드닝 설계

## 목표

DocSearch AI를 포트폴리오용 데모를 넘어 운영 가능한 서비스처럼 보이게 만드는 최소 하드닝 기준선을 추가합니다. 이번 범위에서는 모든 백엔드 응답에 기본 보안 헤더를 붙이고, `/ready` 엔드포인트가 운영 설정 위험을 드러내도록 만듭니다.

## 포함 범위

- 백엔드 응답에 기본 보안 헤더를 추가합니다.
- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`를 기본으로 제공합니다.
- `/ready` 응답에 운영 준비 상태와 설정 점검 결과를 포함합니다.
- 운영 환경에서 개발 기본 API Key를 그대로 쓰는 경우 `not_ready`로 표시합니다.
- 운영 환경에서 `DEBUG=true`인 경우 `not_ready`로 표시합니다.
- README 현재 범위에 운영 하드닝 기준선을 반영합니다.

## 제외 범위

- PostgreSQL, Redis, Qdrant, MinIO, vLLM의 실시간 연결 점검
- Kubernetes readiness/liveness probe 구성
- 관리자 권한 분리
- rate limit, IP allowlist, 감사 로그 보존 정책

## API 설계

`GET /ready`는 기본적으로 다음 형태를 반환합니다.

```json
{
  "status": "ready",
  "service": "docsearch-ai",
  "checks": [
    {
      "name": "configuration",
      "status": "ready",
      "message": "운영 설정 기준을 통과했습니다."
    }
  ]
}
```

운영 설정이 위험하면 HTTP 503과 `not_ready` 상태를 반환합니다.

## 후속 단계

다음 PR에서는 외부 의존성 연결 점검, 관리자 권한 분리, 운영 rate limit을 순차적으로 다룹니다.
