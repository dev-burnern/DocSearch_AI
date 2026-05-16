# Agent Flow 문서

이 문서는 DocSearch AI V2 MVP의 주요 처리 흐름을 기능별로 분리해 설명합니다. 여기서 Agent Flow는 LLM agent framework가 아니라, 문서 처리와 RAG 답변을 구성하는 서비스 흐름을 의미합니다.

## 문서 업로드와 인덱싱

```mermaid
sequenceDiagram
  participant U as User
  participant F as Frontend
  participant A as Backend API
  participant S as MinIO
  participant M as Metadata Store
  participant Q as Job Queue
  participant W as Worker
  participant E as Embedding
  participant V as Qdrant

  U->>F: 파일 업로드
  F->>A: POST /v1/documents
  A->>A: API Key / workspace 확인
  A->>A: 파일 크기와 parser 검증
  A->>S: 원본 문서 저장
  A->>Q: indexing job enqueue
  A->>M: document metadata 저장
  A-->>F: document_id, indexing_status 반환
  W->>Q: job pop
  W->>S: 원본 문서 다운로드
  W->>W: parse / chunk
  W->>E: embedding 생성
  W->>V: chunk vector upsert
  W->>M: indexing_status completed 갱신
```

### 예외 처리

| 상황 | 처리 |
| --- | --- |
| 지원하지 않는 확장자 | `DOCUMENT_UNSUPPORTED_TYPE` |
| 빈 문서 | `DOCUMENT_EMPTY` |
| 깨진 TXT/PDF/DOCX | `DOCUMENT_CORRUPT` |
| 대용량 문서 | `DOCUMENT_TOO_LARGE`, HTTP 413 |
| Redis enqueue 실패 | 문서 상태 `failed`, 운영 이벤트 `indexing.queue_unavailable` |
| worker 처리 실패 | 재시도 가능하면 `queued`, 한도 초과 시 `failed` |

## 검색 흐름

```mermaid
sequenceDiagram
  participant U as User
  participant F as Frontend
  participant A as Backend API
  participant E as Embedder
  participant V as Qdrant

  U->>F: 검색어 입력
  F->>A: POST /v1/search
  A->>A: workspace / document filter 생성
  A->>E: query embedding 생성
  A->>V: vector search
  A->>V: hybrid mode이면 lexical 후보 조회
  A->>A: score 정렬
  A-->>F: snippet 포함 검색 결과 반환
```

### 검색 정책

| 모드 | 동작 |
| --- | --- |
| `dense` | query embedding으로 Qdrant vector search 수행 |
| `hybrid` | dense 후보와 lexical 후보를 합친 뒤 dense/lexical 가중합으로 정렬 |
| document filter | 요청 document_ids가 있으면 같은 workspace 안의 해당 문서로 제한 |

## 채팅 RAG 흐름

```mermaid
sequenceDiagram
  participant U as User
  participant F as Frontend
  participant A as Backend API
  participant R as Retriever
  participant B as Reranker
  participant L as LLM
  participant G as Audit Log

  U->>F: 질문 입력
  F->>A: POST /v1/chat
  A->>R: 관련 chunk 검색
  A->>B: rerank
  A->>A: relevance threshold 필터
  alt 지원 chunk 없음
    A->>G: no-answer 감사 로그 기록
    A-->>F: 모르겠습니다 응답
  else 지원 chunk 있음
    A->>L: context + question 전달
    A->>A: 답변에서 유효 citation 추출
    alt 유효 citation 없음
      A->>G: no-answer 감사 로그 기록
      A-->>F: 모르겠습니다 응답
    else citation 있음
      A->>G: 답변과 citation 감사 로그 기록
      A-->>F: answer, usage, citations 반환
    end
  end
```

### Grounding 정책

| 단계 | 정책 |
| --- | --- |
| retrieval 결과 없음 | LLM 호출 없이 no-answer |
| rerank relevance 부족 | LLM 호출 없이 no-answer |
| LLM 답변 citation 없음 | no-answer |
| LLM 답변 범위 밖 citation만 있음 | no-answer |
| LLM 답변 citation 중복 | 첫 citation만 유지 |
| 응답 citations | 답변 본문에 실제 표시된 `[n]`만 반환 |

## 감사 로그와 운영 이벤트

```mermaid
flowchart TD
  Chat["Chat API"] --> Audit["Audit Log Store"]
  Audit --> AdminAudit["Admin Audit UI"]
  Ready["/ready"] --> Operations["Operation Event Store"]
  Worker["Indexing Worker"] --> Operations
  Queue["Redis Queue"] --> Operations
  Operations --> AdminOps["Admin Operations UI"]
```

| 이벤트 | 발생 위치 | 확인 위치 |
| --- | --- | --- |
| `dependency.health_failed` | `/ready`, `/v1/admin/operations` dependency check | 관리자 운영 상태 |
| `indexing.queue_unavailable` | Redis enqueue 실패 | 관리자 운영 상태 |
| `indexing.retry_scheduled` | worker 실패 후 재시도 예약 | 관리자 운영 상태 |
| `indexing.failed` | worker 최종 실패 또는 in-process 실패 | 관리자 운영 상태 |
| chat audit event | 채팅 답변 생성 | 감사 로그 화면, CSV export |

## 로컬 노트북 검증 흐름

1. Notebook Compose로 AI stub 기반 전체 서비스를 실행합니다.
2. `local-dev-key`로 로그인합니다.
3. 작은 TXT 문서를 업로드합니다.
4. 문서 목록에서 `indexing_status=completed`를 확인합니다.
5. 검색 화면에서 문서 내용이 검색되는지 확인합니다.
6. 채팅 화면에서 답변, citation, 감사 로그가 생성되는지 확인합니다.
7. 운영 상태에서 dependency, model setting, indexing queue 상태를 확인합니다.

이 흐름은 기능 계약 검증용입니다. 실제 vLLM/BGE 품질과 latency는 별도 GPU 환경에서 측정합니다.
