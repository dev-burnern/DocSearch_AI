# 운영 Rate Limit 설계

## 목표

DocSearch AI의 운영 API가 짧은 시간에 과도하게 호출되는 상황을 막기 위해 `/v1/*` 요청에 rate limit을 적용한다. 헬스 체크, readiness, 문서 페이지는 제한 대상에서 제외해 운영 모니터링과 개발 편의성을 유지한다.

## 범위

- API Key가 있으면 API Key 단위로 요청량을 제한한다.
- API Key가 없으면 클라이언트 IP 단위로 요청량을 제한한다.
- 제한 초과 시 HTTP 429와 `Retry-After` 헤더를 반환한다.
- 개발 환경 기본값은 비활성화, 운영 환경 기본값은 활성화한다.
- 현재 단계에서는 단일 API 컨테이너 기준의 인메모리 제한으로 구현한다.

## 제외 범위

- 여러 API 인스턴스 간 공유 제한은 Redis 기반 구현으로 후속 전환한다.
- 사용자별 세부 정책, 엔드포인트별 별도 제한, 관리자 예외 처리는 이번 범위에 포함하지 않는다.

## 설정

- `RATE_LIMIT_ENABLED`: rate limit 활성화 여부
- `RATE_LIMIT_REQUESTS`: 윈도우 안에서 허용할 최대 요청 수
- `RATE_LIMIT_WINDOW_SECONDS`: 요청 제한 윈도우 길이

## 응답 계약

제한을 초과하면 다음 형식으로 응답한다.

```json
{
  "detail": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please retry later."
  }
}
```

응답 헤더에는 `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`을 포함한다.
