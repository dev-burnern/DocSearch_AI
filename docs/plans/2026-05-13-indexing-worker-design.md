# DocSearch AI Indexing Worker Design

## 목표

문서 업로드 이후 바로 인덱싱 잡을 만들고, 개발 환경에서는 API 프로세스 안에서 같은 흐름을 동기 실행해 청킹과 임베딩까지 연결한다. Redis 기반 워커는 이번 단계에서 실행 경계와 직렬화 포맷만 정리하고, 실제 소비 루프는 다음 배치로 넘긴다.

## 범위

- 업로드 응답에 인덱싱 잡 정보 포함
- 인덱싱 잡 모델과 큐 인터페이스 추가
- 개발용 인프로세스 큐 추가
- 문서 다운로드 -> 파싱 -> 청킹 -> 임베딩 파이프라인 추가
- README의 `llm` 표기를 `vLLM`로 정리

## 설계 원칙

1. 업로드 API는 큐 구현체를 직접 몰라야 한다.
2. 인덱싱 파이프라인은 이후 Redis 워커와 재사용 가능해야 한다.
3. 벡터 저장소 연동 전까지는 청킹과 임베딩 결과를 메모리 결과 객체로만 반환한다.
4. 외부 모델 호출은 아직 붙이지 않고, 결정적 결과를 내는 개발용 임베더를 사용한다.

## 데이터 흐름

1. 사용자가 문서를 업로드한다.
2. `DocumentService`가 원본 파일을 MinIO에 저장한다.
3. `DocumentService`가 `IndexDocumentJob`을 생성해 `JobQueue`에 전달한다.
4. 개발 환경에서는 `InProcessJobQueue`가 즉시 `IndexingPipeline`을 실행한다.
5. `IndexingPipeline`은 저장소에서 원본을 다시 읽고, 파서 레지스트리로 텍스트를 추출한다.
6. `Chunker`가 텍스트를 청크로 나누고, `Embedder`가 각 청크에 대한 임베딩을 만든다.
7. 업로드 응답에는 `indexing_job_id`, `indexing_status`, `chunk_count`를 포함한다.

## 후속 단계로 미루는 것

- Redis 큐 실제 소비 루프
- Celery 또는 별도 워커 런타임
- Qdrant 저장
- BGE-M3 실제 임베딩 호출
- 인덱싱 상태 영속화와 조회 API
