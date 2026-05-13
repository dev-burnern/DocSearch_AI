# DocSearch AI Retrieval Design

## 목표

인덱싱된 문서 청크를 Qdrant에 저장하고, 워크스페이스 기준 메타데이터 필터를 적용한 Dense Retrieval 서비스를 추가한다. 이번 단계에서는 검색 API를 만들지 않고, 저장소와 서비스 경계를 먼저 고정한다.

## 범위

- 인덱싱 파이프라인이 청크 임베딩을 Qdrant에 저장
- Qdrant 컬렉션 생성과 upsert/search 경계 추가
- 워크스페이스 및 문서 기준 메타데이터 필터 추가
- Dense Retrieval 서비스 추가
- README의 `llm` 표기를 `vLLM`로 정리

## 설계 원칙

1. 업로드와 인덱싱 흐름은 검색 계층을 직접 알지 않고 `QdrantVectorStore` 경계만 사용한다.
2. Retrieval 서비스는 이후 `chat-api` PR에서 그대로 재사용할 수 있어야 한다.
3. 이번 단계에서는 reranker를 붙이지 않고, Dense search 결과만 안정적으로 반환한다.
4. 테스트는 실제 Qdrant 서버 대신 `qdrant-client`의 로컬 메모리 모드를 우선 사용한다.

## 데이터 흐름

1. `IndexingPipeline`이 청크와 임베딩 벡터를 생성한다.
2. `QdrantVectorStore`가 컬렉션을 보장하고 청크를 payload와 함께 upsert한다.
3. `DenseRetriever`는 질의 문자열을 임베딩한 뒤 `QdrantVectorStore.search()`를 호출한다.
4. `RetrievalFilter`가 워크스페이스와 선택 문서 조건을 Qdrant 필터로 변환한다.
5. 반환 결과는 `score`, `chunk_text`, `document_id`, `filename`, `chunk_index`를 포함한다.

## 후속 단계로 미루는 것

- reranker 실제 적용
- 검색 API 및 채팅 API
- 하이브리드 검색
- 권한 레벨, 태그, 날짜 기준 고급 필터
