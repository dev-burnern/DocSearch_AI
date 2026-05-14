# 감사 로그 PostgreSQL 영속화 설계

## 목표

인메모리 감사 로그를 PostgreSQL 저장소로 확장해 서버 재시작 이후에도 채팅 감사 이벤트를 유지합니다. 기존 API 계약은 유지하고, 저장소 구현만 `AUDIT_LOG_BACKEND` 설정으로 선택할 수 있게 합니다.

## 범위

- PostgreSQL 감사 로그 저장소 추가
- `chat_audit_events` 테이블 자동 생성
- 감사 이벤트 payload를 JSONB로 저장
- 워크스페이스 ID와 발생 시각 기준 조회
- 로컬 Compose 기본값을 PostgreSQL 감사 로그 모드로 설정

## 제외 범위

- Alembic 마이그레이션 체계
- 관리자 권한 분리
- 감사 로그 보존 기간과 삭제 정책
- 복합 검색 필터
- 감사 로그 프론트엔드 화면

## 저장 구조

테이블은 조회에 필요한 대표 컬럼과 전체 이벤트 payload를 함께 저장합니다.

- `event_id`: 이벤트 고유 ID
- `request_id`: 요청 추적 ID
- `workspace_id`: 워크스페이스 필터 키
- `workspace_name`: 표시 이름
- `event_type`: 이벤트 종류
- `occurred_at`: 이벤트 발생 시각
- `event_payload`: `ChatAuditEvent` 전체 JSONB

## 후속 작업

다음 단계에서는 프론트엔드 채팅 플로우를 연결하고, 이후 감사 로그 조회 UI와 관리자 권한 분리를 별도 PR로 진행합니다.
