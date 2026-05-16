# PR 단위 개발 히스토리

## 요약

DocSearch AI V2는 `develop` 브랜치를 기준으로 기능을 작은 PR 단위로 누적했습니다. 초기 스캐폴드부터 문서 처리, 검색, 채팅, 운영, 감사 로그, 인증/권한, 포트폴리오 정리까지 단계적으로 확장했습니다.

## 주요 PR 흐름

| PR | 구분 | 내용 |
| --- | --- | --- |
| #3 | 스캐폴드 | FastAPI, React, Docker Compose 기준 서비스 구조 재정비 |
| #4 | 인증 | API Key 기반 workspace context 추가 |
| #5 | 문서 | 문서 업로드, parser 경계, 원본 저장 구조 추가 |
| #6 | 인덱싱 | 인덱싱 worker와 인프로세스 큐 추가 |
| #7 | 검색 | Qdrant 저장소와 dense retrieval 추가 |
| #8 | LLM | vLLM/OpenAI compatible gateway 추가 |
| #9 | 채팅 | 출처 포함 채팅 API 추가 |
| #10 | 리랭킹 | BGE reranker 경계와 채팅 연결 |
| #11 | 감사 | 채팅 감사 로그 경계 추가 |
| #13 | 감사 | PostgreSQL 감사 로그 영속화 |
| #14 | 프론트 | 채팅 화면 연결 |
| #16 | 프론트 | 문서 업로드와 검색 화면 연결 |
| #17 | 문서 | 업로드 문서 목록 조회 |
| #18 | 감사 | 감사 로그 조회 필터 |
| #19 | 문서 | 문서 삭제와 재인덱싱 |
| #20 | 감사 | 감사 로그 CSV 내보내기 |
| #21 | 운영 | 운영 하드닝 기준선 |
| #22 | 권한 | 관리자 권한 분리 |
| #23 | 운영 | 외부 의존성 상태 점검 |
| #24 | 프론트 | 관리자 화면 표시 조건 |
| #25 | 운영 | rate limit 적용 |
| #26 | 운영 | 관리자 운영 상태 화면 |
| #27 | 운영 | Redis 기반 rate limit 전환 |
| #28 | 운영 | 운영 이벤트 알림 경계 |
| #29 | 인덱싱 | 인덱싱 실패 상태 기록 |
| #30 | 인덱싱 | Redis 큐 재시도 처리 |
| #31 | 문서 | 문서 처리 안정성 개선 |
| #32 | RAG | 채팅 근거 품질 개선 |
| #33 | LLM | vLLM timeout/retry 정책 |
| #34 | 문서 | LLM 운영 가이드 |
| #35 | Embedding | BGE-M3 embedding backend |
| #36 | 검색 | hybrid search 정책 |
| #37 | RAG | citation 반환 정확도 개선 |
| #38 | RAG | 근거 없는 답변 차단 |
| #39 | 운영 | 인덱싱 큐 대기건수 표시 |
| #41 | 안정화 | 로컬 인덱싱 검증 흐름 안정화 |
| #42 | 인증/문서 | 사번 로그인, 회원가입, 문서 보안등급 UI |
| #43 | 권한 | 보안등급 접근 정책 적용 |

## 개발 단계별 성과

| 단계 | 성과 |
| --- | --- |
| 기반 구축 | API, frontend, gateway, worker, DB, Redis, Qdrant, MinIO 구성 |
| 문서 처리 | 파일 업로드부터 parser, metadata, queue, vector upsert까지 연결 |
| RAG 품질 | dense retrieval, hybrid search, reranker, citation 검증, 모른다 처리 |
| 운영성 | health/readiness, dependency check, operation event, rate limit, admin 화면 |
| 보안/권한 | 사번 로그인, API Key 호환, admin/member, 문서 보안등급 정책 |
| 포트폴리오 | 로컬 노트북 실행 가이드, LLM 운영 가이드, 테스트 기준 문서화 |

## 리뷰 단위 원칙

- API, 저장소, UI, 문서를 가능한 한 독립 PR로 분리했습니다.
- 기능 변경과 문서 변경이 성격상 다르면 별도 커밋으로 분리했습니다.
- 각 PR은 로컬 테스트 또는 GitHub Actions 결과를 PR 설명에 기록했습니다.
- 후속 보완이 필요한 내용은 다음 PR로 넘겨 히스토리를 추적 가능하게 유지했습니다.
