# 감사 로그 PostgreSQL 영속화 구현 계획

## 1단계: 테스트 기준선

- PostgreSQL 저장소가 테이블과 인덱스를 보장하는지 검증합니다.
- 감사 이벤트가 JSONB payload로 저장되는지 검증합니다.
- JSONB payload를 다시 `ChatAuditEvent`로 복원하는지 검증합니다.
- 설정값에 따라 인메모리/PostgreSQL 저장소가 선택되는지 검증합니다.

## 2단계: 저장소 구현

- `PostgresAuditLogStore`를 추가합니다.
- `chat_audit_events` 테이블을 자동 생성합니다.
- `record_chat_event`, `list_chat_events`를 PostgreSQL 기반으로 구현합니다.

## 3단계: 런타임 연결

- `DATABASE_URL`, `AUDIT_LOG_BACKEND` 설정을 추가합니다.
- 감사 로그 라우터의 저장소 생성 로직을 설정 기반 factory로 분리합니다.
- Compose 기본 환경을 PostgreSQL 감사 로그 모드로 맞춥니다.

## 4단계: 문서 갱신

- README 현재 범위에 PostgreSQL 감사 로그 저장소를 반영합니다.
- `.env.example`에 감사 로그 백엔드 설정을 추가합니다.
- 설계 문서에 JSONB 저장 구조와 제외 범위를 남깁니다.
