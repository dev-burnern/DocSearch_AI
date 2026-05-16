# LLM 운영 가이드

이 문서는 DocSearch AI V2 MVP에서 vLLM/OpenAI compatible LLM 게이트웨이를 운영할 때 확인해야 하는 설정, 장애 정책, 로컬 GPU별 모델 선택 기준을 정리합니다.

## 운영 전제

- DocSearch AI 백엔드는 OpenAI compatible `POST /chat/completions` 계약만 바라봅니다.
- embedding 백엔드는 기본 deterministic 모드와 OpenAI compatible `POST /embeddings` 모드를 지원합니다.
- 온프레미스 기준은 모델 가중치와 추론 서버를 사내 또는 로컬 GPU 환경에서 직접 실행하는 구성입니다.
- `LLM_API_KEY`는 보호된 compatible endpoint를 붙일 때만 사용합니다. 기본 로컬 vLLM 구성에서는 비워둡니다.
- `LLM_MODEL` 값은 실제 vLLM 서버에 올라간 모델 ID와 반드시 같아야 합니다.
- 현재 코드 기본값은 `google/gemma-4-E4B-it`입니다. 실제 운영 모델을 바꾸면 `.env`, compose, 배포 환경의 `LLM_MODEL`도 함께 바꿉니다.

## 설정 정책

| 환경 변수 | 기본값 | 운영 기준 |
| --- | --- | --- |
| `LLM_BASE_URL` | `http://llm:8000/v1` | API 컨테이너에서 접근 가능한 vLLM OpenAI compatible base URL |
| `LLM_MODEL` | `google/gemma-4-E4B-it` | vLLM에 로드한 모델 ID |
| `LLM_API_KEY` | 빈 값 | 로컬 vLLM은 비움, 보호된 endpoint만 설정 |
| `LLM_TIMEOUT_SECONDS` | `30.0` | 모델 cold start나 장문 컨텍스트가 있으면 늘리되 gateway timeout보다 낮게 유지 |
| `LLM_MAX_TOKENS` | `1024` | 답변 길이와 latency 예산에 맞춰 조정 |
| `LLM_TEMPERATURE` | `0.2` | RAG 답변은 낮은 값을 기본으로 사용 |
| `LLM_MAX_RETRIES` | `2` | 네트워크 오류, HTTP 429, HTTP 5xx에만 재시도 |
| `LLM_RETRY_BACKOFF_SECONDS` | `0.5` | 짧은 순간 장애 흡수를 위한 고정 backoff |
| `EMBEDDING_BACKEND` | `deterministic` | 운영 BGE-M3 서버를 붙이면 `bge`로 변경 |
| `EMBEDDING_BASE_URL` | `http://embedding:8002/v1` | OpenAI compatible embedding base URL |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | embedding 서버에 로드한 모델 ID |
| `EMBEDDING_VECTOR_SIZE` | `8` | deterministic 기본값. BGE-M3는 보통 `1024`로 맞춤 |
| `EMBEDDING_TIMEOUT_SECONDS` | `10.0` | embedding 요청 timeout |
| `RETRIEVAL_MODE` | `dense` | `hybrid`로 바꾸면 dense score와 lexical score를 함께 반영 |
| `HYBRID_DENSE_WEIGHT` | `0.7` | hybrid search에서 vector similarity 반영 비율 |
| `HYBRID_LEXICAL_WEIGHT` | `0.3` | hybrid search에서 query term overlap 반영 비율 |
| `HYBRID_CANDIDATE_LIMIT` | `50` | hybrid score를 계산할 후보 chunk 수 |

## 장애 처리 기준

- HTTP 429와 HTTP 5xx는 transient 장애로 보고 `LLM_MAX_RETRIES`만큼 재시도합니다.
- 네트워크 오류는 같은 재시도 정책을 적용합니다.
- HTTP 400 계열 검증 오류는 요청 또는 모델 계약 문제로 보고 재시도하지 않습니다.
- 재시도 후에도 실패하면 채팅 API는 `CHAT_LLM_UNAVAILABLE` 계열 오류로 변환합니다.
- 운영 화면의 `/v1/admin/operations` 응답에서 현재 LLM 모델, timeout, max tokens, temperature, retry 설정을 확인합니다.
- `EMBEDDING_BACKEND=bge`이면 `/ready`가 embedding 서버의 `/models` endpoint도 점검합니다.

## BGE-M3 embedding 운영 흐름

1. 문서 업로드 또는 재인덱싱이 들어오면 파서가 문서 본문을 추출합니다.
2. chunker가 본문을 검색 단위 chunk로 나눕니다.
3. `EMBEDDING_BACKEND=bge`이면 BGE embedding client가 `/embeddings` endpoint에 chunk 목록을 보냅니다.
4. 응답 embedding 개수와 vector dimension을 검증한 뒤 Qdrant에 저장합니다.
5. 검색과 채팅 질문도 같은 embedding backend로 vector를 만든 뒤 Qdrant에서 조회합니다.

운영에서는 문서 인덱싱과 검색이 같은 embedding 모델, 같은 vector size, 같은 Qdrant collection을 사용해야 합니다. 모델이나 dimension을 바꾸면 기존 collection을 비우거나 새 collection 이름을 사용합니다.

## Hybrid search 운영 흐름

`RETRIEVAL_MODE=dense`는 embedding vector score만 사용합니다. `RETRIEVAL_MODE=hybrid`는 Qdrant dense 후보와 같은 workspace/document filter 안의 lexical 후보를 함께 모은 뒤, dense score와 query term overlap score를 가중 합산합니다.

기본 가중치는 dense 0.7, lexical 0.3입니다. 문서명이 아니라 chunk 본문 기준으로 lexical score를 계산하므로, 정확한 키워드가 들어간 chunk를 dense 후보보다 위로 보정하는 용도입니다. 대규모 운영에서는 `HYBRID_CANDIDATE_LIMIT`을 너무 크게 잡으면 Qdrant scroll 비용이 커질 수 있으므로 latency 측정 후 조정합니다.

## 로컬 GPU별 모델 선택 시작점

아래 표는 2026-05-16 기준 운영 시작점입니다. 실제 사용 가능 여부는 GPU VRAM, CUDA/driver, vLLM 버전, `max-model-len`, 동시 요청 수, RAG 컨텍스트 길이에 따라 달라집니다.

| 로컬 GPU 기준 | 우선 모델 | 설정 예시 | 적용 기준 |
| --- | --- | --- | --- |
| 8-12GB VRAM | `Qwen/Qwen3-8B-AWQ` | `LLM_MODEL=Qwen/Qwen3-8B-AWQ`, `LLM_MAX_TOKENS=512-1024` | 단일 사용자 데모, 짧은 컨텍스트, latency 우선 |
| 16-24GB VRAM | `Qwen/Qwen3-14B-AWQ` | `LLM_MODEL=Qwen/Qwen3-14B-AWQ`, `LLM_MAX_TOKENS=1024` | 포트폴리오 데모 기본 후보, 품질과 비용 균형 |
| 24-48GB VRAM | `Qwen/Qwen3-32B-AWQ` | `LLM_MODEL=Qwen/Qwen3-32B-AWQ`, `LLM_MAX_TOKENS=1024-2048` | 답변 품질 우선, latency와 VRAM 여유가 있을 때 |
| VRAM 부족 또는 CPU 검증 | 더 작은 instruct 모델 또는 낮은 `max-model-len` | `LLM_TIMEOUT_SECONDS` 증가, `LLM_MAX_TOKENS` 축소 | 기능 검증용. 운영 품질 기준으로 보지 않음 |

Qwen3 AWQ 모델은 4-bit AWQ 양자화 모델입니다. vLLM의 quantization 호환성 표는 AWQ가 Turing, Ampere, Ada, Hopper 계열에서 지원된다고 설명하지만, 표 자체가 vLLM 버전에 따라 바뀔 수 있으므로 실제 배포 전에는 사용하는 vLLM 이미지 기준으로 다시 확인합니다.

## vLLM 실행 예시

로컬에서 vLLM을 직접 띄울 때는 모델 ID와 API 설정을 같은 값으로 맞춥니다.

```bash
vllm serve Qwen/Qwen3-14B-AWQ --host 0.0.0.0 --port 8000
```

compose 내부 API가 이 서버를 바라보게 할 때:

```env
LLM_BASE_URL=http://llm:8000/v1
LLM_MODEL=Qwen/Qwen3-14B-AWQ
LLM_TIMEOUT_SECONDS=30.0
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.2
LLM_MAX_RETRIES=2
LLM_RETRY_BACKOFF_SECONDS=0.5
```

호스트에서 별도 vLLM을 띄우고 API만 연결하는 경우에는 `LLM_BASE_URL`을 API 컨테이너에서 접근 가능한 주소로 바꿉니다. Windows Docker Desktop 기준으로는 보통 `http://host.docker.internal:8000/v1`을 사용합니다.

## 운영 검증 체크리스트

- `/ready`에서 `vllm` dependency check가 ready인지 확인합니다.
- `/v1/admin/operations`에서 실제 모델명과 retry 설정이 의도한 값인지 확인합니다.
- 같은 문서와 질문으로 3회 이상 채팅해 citation이 유지되는지 확인합니다.
- vLLM 서버를 잠시 내렸을 때 LLM 장애가 운영 이벤트 또는 관리자 화면에서 확인되는지 확인합니다.
- 모델 변경 후에는 API 응답 시간, 검색 latency, 채팅 응답 시간을 다시 기록합니다.

## 근거 링크

- vLLM quantization compatibility: https://docs.vllm.ai/en/stable/features/quantization/index.html
- Qwen3-8B-AWQ model card: https://huggingface.co/Qwen/Qwen3-8B-AWQ
- Qwen3-14B-AWQ model card: https://huggingface.co/Qwen/Qwen3-14B-AWQ
- Qwen3-32B-AWQ model card: https://huggingface.co/Qwen/Qwen3-32B-AWQ
