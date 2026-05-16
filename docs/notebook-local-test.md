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
- hybrid search score blend 경계
- OpenAI compatible `/chat/completions` 호출 경계
- 검색, 채팅, citation, 감사 로그 화면 흐름
- 사번 로그인과 문서 보안등급 접근 정책
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

## 포트폴리오 화면용 host LLM 연결

Ollama 또는 LM Studio처럼 Windows 호스트에서 OpenAI compatible local server를 실행하면, Docker 안의 API만 해당 서버를 바라보게 바꿀 수 있습니다. 이 구성은 embedding stub은 그대로 두고 채팅 LLM만 실제 모델로 바꾸므로 기존 Qdrant collection을 다시 만들 필요가 없습니다.

Ollama 기본 서버를 사용할 때:

```powershell
$env:LOCAL_LLM_BASE_URL = "http://host.docker.internal:11434/v1"
$env:LOCAL_LLM_MODEL = "gemma3:4b"
$env:LOCAL_LLM_TIMEOUT_SECONDS = "180.0"
$env:LOCAL_LLM_MAX_TOKENS = "384"
$env:LOCAL_LLM_TEMPERATURE = "0.0"
$env:LOCAL_CHAT_RETRIEVAL_LIMIT = "3"
$env:LOCAL_CHAT_RERANK_TOP_K = "1"
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.notebook.yml -f infra/compose/docker-compose.host-llm.yml up --build -d api gateway
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.notebook.yml -f infra/compose/docker-compose.host-llm.yml restart gateway
```

포트폴리오 화면을 빠르게 확인할 때는 채팅 화면의 `검색 개수`를 `1`로 낮춰 테스트합니다. `gemma3:4b` CPU 모드는 `검색 개수 1`에서는 짧은 답변 확인이 가능하지만, `검색 개수 5`는 컨텍스트가 길어져 응답이 1분 이상 걸릴 수 있습니다.

LM Studio 기본 서버를 사용할 때:

```powershell
$env:LOCAL_LLM_BASE_URL = "http://host.docker.internal:1234/v1"
$env:LOCAL_LLM_MODEL = "<LM Studio에서 로드한 모델 ID>"
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.notebook.yml -f infra/compose/docker-compose.host-llm.yml up --build -d api gateway
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.notebook.yml -f infra/compose/docker-compose.host-llm.yml restart gateway
```

## 빠른 확인 순서

1. `http://localhost:8080`에서 `2301029 / password`로 관리자 로그인합니다.
2. 작은 `.txt` 파일을 업로드합니다.
3. 문서 업로드 시 보안등급을 지정하고 업로드 결과를 확인합니다.
4. 문서 검색에서 업로드한 문서 내용으로 검색합니다.
5. 채팅에서 같은 내용을 질문하고 출처가 표시되는지 확인합니다.
6. 관리자 운영 상태에서 `llm`, `embedding`, `qdrant`, `minio` 상태가 ready인지 확인합니다.
