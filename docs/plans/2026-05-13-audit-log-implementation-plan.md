# 감사 로그 구현 계획

## 1단계: 테스트 기준선

- 감사 로그 저장소가 워크스페이스별 이벤트를 분리해 조회하는지 검증합니다.
- 감사 로그 조회 API가 인증된 워크스페이스의 이벤트만 반환하는지 검증합니다.
- 채팅 서비스가 성공 응답 후 감사 이벤트를 기록하는지 검증합니다.

## 2단계: 감사 로그 경계 추가

- `AuditCitation`, `ChatAuditEvent`, `ChatAuditEventListResponse` 모델을 정의합니다.
- `AuditLogStore` 프로토콜과 `InMemoryAuditLogStore`를 추가합니다.
- 감사 로그 조회 라우터를 추가합니다.

## 3단계: 채팅 흐름 연결

- `ChatService`에 감사 로그 저장소를 주입합니다.
- 답변 생성 성공 후 request/workspace/question/citation/token 정보를 이벤트로 기록합니다.
- 답변 전문 대신 preview와 문자 수를 남깁니다.

## 4단계: 문서 갱신

- README 현재 범위에 인메모리 감사 로그 경계를 반영합니다.
- 설계 문서에 영속화 제외 범위와 후속 PostgreSQL 작업을 남깁니다.
