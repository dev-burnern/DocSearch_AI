# 노트북 로컬 테스트 가이드

Galaxy Book6 Pro 풀옵션 같은 얇은 노트북 환경에서는 NVIDIA CUDA가 없을 수 있습니다. 이 경우 기본 vLLM 컨테이너를 그대로 띄우면 모델 서버 단계에서 막힐 수 있으므로, 로컬 통합 테스트는 가벼운 AI stub으로 먼저 검증합니다.

## 실행 명령

```bash
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.notebook.yml up --build
```

접속 주소는 기본 compose와 같습니다.

- 게이트웨이: `http://localhost:8080`
- 백엔드 문서: `http://localhost:8000/docs`
- 프론트엔드 개발 서버: `http://localhost:5173`
- MinIO 콘솔: `http://localhost:9001`
- 로컬 AI stub: `http://localhost:8100/v1`

## 이 구성이 검증하는 것

- 문서 업로드, 파싱, 청킹, Qdrant 저장 흐름
- OpenAI compatible `/embeddings` 호출 경계
- OpenAI compatible `/chat/completions` 호출 경계
- 검색, 채팅, citation, 감사 로그 화면 흐름
- 관리자 운영 상태에서 LLM과 embedding dependency check 확인

## 이 구성이 검증하지 않는 것

- 실제 BGE-M3 임베딩 품질
- 실제 vLLM 모델 latency와 VRAM 사용량
- 실제 reranker 품질
- 대용량 문서 처리 성능

## 실제 BGE-M3 embedding 서버를 붙일 때

노트북에서 별도 embedding 서버를 실행하거나 다른 장비의 endpoint를 붙일 수 있으면 아래 환경 변수만 바꿉니다.

```env
EMBEDDING_BACKEND=bge
EMBEDDING_BASE_URL=http://host.docker.internal:8002/v1
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_VECTOR_SIZE=1024
EMBEDDING_TIMEOUT_SECONDS=10.0
```

`EMBEDDING_VECTOR_SIZE`는 Qdrant collection 크기와 맞아야 합니다. deterministic 8차원으로 만든 collection을 BGE-M3 1024차원으로 재사용하면 upsert나 검색이 실패할 수 있으므로, 모델을 바꿀 때는 collection을 비우거나 새 collection 이름을 사용합니다.

## 빠른 확인 순서

1. `http://localhost:8080`에서 `local-dev-key`를 입력합니다.
2. 작은 `.txt` 파일을 업로드합니다.
3. 문서 검색에서 업로드한 문서 내용으로 검색합니다.
4. 채팅에서 같은 내용을 질문하고 출처가 표시되는지 확인합니다.
5. 관리자 운영 상태에서 `llm`, `embedding`, `qdrant`, `minio` 상태가 ready인지 확인합니다.
