# 리랭커 구현 계획

## 1단계: 테스트 기준선

- score-preserving 리랭커가 기존 검색 순서와 점수를 유지하는지 검증합니다.
- BGE 클라이언트가 `/rerank`에 표준 요청을 보내고 응답 순서대로 청크를 반환하는지 검증합니다.
- BGE 클라이언트가 HTTP 실패와 잘못된 index를 공급자 오류로 변환하는지 검증합니다.
- 기본 리랭커 프로필이 환경 변수를 반영하는지 검증합니다.
- 채팅 서비스가 리랭커 순서대로 컨텍스트와 출처를 구성하는지 검증합니다.

## 2단계: 리랭커 경계 추가

- `Reranker`, `RerankRequest`, `RerankedChunk`, `RerankerProviderError`를 정의합니다.
- 로컬 fallback인 `ScorePreservingReranker`를 추가합니다.
- BGE 호환 HTTP 클라이언트와 프로필을 추가합니다.

## 3단계: 채팅 흐름 연결

- `ChatService`에 리랭커 의존성을 주입합니다.
- Dense retrieval 결과를 리랭커에 전달한 뒤, 리랭커 결과 순서로 컨텍스트를 구성합니다.
- `ChatCitation`에 `rerank_score`를 추가합니다.
- 리랭커 공급자 오류를 `CHAT_RERANKER_UNAVAILABLE`로 변환합니다.

## 4단계: 문서와 설정 갱신

- `.env.example`에 리랭커 런타임 설정을 추가합니다.
- Docker Compose의 API 환경 변수에 리랭커 기본값을 추가합니다.
- README와 설계 문서에 fallback 모드와 BGE 모드 전환 방식을 남깁니다.
