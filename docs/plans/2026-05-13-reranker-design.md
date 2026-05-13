# 리랭커 설계

## 목표

Dense retrieval 결과를 그대로 답변 컨텍스트에 넣지 않고, 질문과 청크의 관련도를 다시 계산해 더 적합한 청크가 앞에 오도록 정렬합니다. MVP에서는 서비스 내부 리랭커 인터페이스와 BGE 호환 HTTP 클라이언트를 추가하고, 로컬 실행 기본값은 기존 검색 점수를 보존하는 fallback으로 둡니다.

## 범위

- `Reranker` 인터페이스와 `RerankRequest`, `RerankedChunk` 계약 정의
- BGE 호환 `/rerank` HTTP 클라이언트 추가
- 리랭커 프로필과 환경 변수 설정 추가
- 채팅 서비스에서 검색 결과와 컨텍스트 빌더 사이에 리랭커 삽입
- 응답 출처에 `rerank_score` 포함

## 제외 범위

- 리랭커 모델 서버 이미지 고정
- GPU/CPU 배포 전략
- 리랭커 결과 캐싱
- 감사 로그 저장
- 프론트엔드 표시 방식 변경

## 런타임 모드

`RERANKER_BACKEND=score`는 검색 결과의 기존 점수를 유지합니다. 로컬에서 별도 리랭커 서버를 준비하지 않아도 채팅 API를 사용할 수 있게 하기 위한 기본값입니다.

`RERANKER_BACKEND=bge`는 `RERANKER_BASE_URL`의 BGE 호환 `/rerank` 엔드포인트를 호출합니다. 요청은 `model`, `query`, `documents`, `top_n`을 포함하고, 응답은 `results[].index`, `results[].relevance_score` 형식을 기대합니다.

## 후속 작업

다음 단계에서는 채팅 요청과 답변, 검색/리랭킹 메타데이터를 감사 로그로 저장하고, 프론트엔드에서 출처와 리랭킹 점수를 확인할 수 있게 연결합니다.
