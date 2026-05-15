# Redis 기반 분산 Rate Limit 설계

## 목표

기존 인메모리 rate limit은 단일 API 컨테이너에서는 충분하지만, 여러 API 인스턴스를 띄우면 인스턴스마다 요청 카운터가 분리된다. Redis 기반 저장소를 추가해 API 인스턴스가 여러 개여도 동일한 제한 정책을 공유하도록 한다.

## 설계 방향

- 기존 `/v1/*` 제한 대상과 응답 계약은 유지한다.
- `RATE_LIMIT_BACKEND=memory|redis`로 저장소를 선택한다.
- 기본값은 `memory`로 두어 로컬 단위 테스트와 단일 컨테이너 실행을 안정적으로 유지한다.
- Compose 환경은 Redis 서비스가 있으므로 `RATE_LIMIT_BACKEND=redis`를 명시한다.
- Redis key에는 API Key 원문을 넣지 않고 SHA-256 해시를 사용한다.
- Redis 장애 시 기본값은 fail-open으로 두어 운영 API 전체가 500으로 흔들리지 않게 한다.

## Redis 알고리즘

Redis sorted set을 사용한 sliding window 방식으로 구현한다.

1. 버킷별 key를 만든다.
2. 현재 시각 기준 윈도우 밖의 score를 제거한다.
3. 남은 요청 수가 제한값 이상이면 차단한다.
4. 허용 가능한 요청이면 현재 요청을 sorted set에 추가한다.
5. key TTL을 window 길이에 맞춰 갱신한다.

위 작업은 Lua script로 실행해 여러 API 인스턴스가 동시에 접근해도 카운터 갱신이 원자적으로 처리되게 한다.

## 설정

- `RATE_LIMIT_BACKEND`: `memory` 또는 `redis`
- `RATE_LIMIT_REDIS_PREFIX`: Redis key prefix
- `RATE_LIMIT_FAIL_OPEN`: Redis 장애 시 요청 통과 여부
- 기존 `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`는 그대로 사용한다.

## 운영 상태 화면

관리자 운영 상태 API와 화면에는 rate limit backend와 fail-open 설정을 함께 표시한다. 민감 정보인 API Key, Redis URL, DB URL, Secret은 응답에 포함하지 않는다.

## 제외 범위

- 사용자별 또는 엔드포인트별 별도 제한 정책은 이번 범위에서 제외한다.
- Redis Cluster/Sentinel 전용 설정은 이번 범위에서 제외한다.
- rate limit 초과 이벤트 알림은 다음 단계에서 다룬다.
