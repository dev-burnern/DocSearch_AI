# 채팅 API 설계

## 목표

문서 검색 결과를 vLLM 게이트웨이에 연결해 사용자가 질문을 보내면 권한이 허용된 문서 컨텍스트만 기반으로 답변을 받는 API를 제공합니다. MVP에서는 백엔드 경계를 먼저 고정하고, 프론트엔드 채팅 화면은 다음 단계에서 연결합니다.

## 범위

- `POST /v1/chat` 엔드포인트 추가
- API Key 기반 워크스페이스 인증 재사용
- 워크스페이스와 선택 문서 기준 검색 필터 적용
- 검색된 청크를 RAG 컨텍스트로 구성
- vLLM 게이트웨이에 질문과 컨텍스트 전달
- 답변, 모델명, 토큰 사용량, 출처 목록 반환

## 제외 범위

- 리랭커 실제 연결
- 감사 로그 저장
- 스트리밍 응답
- 프론트엔드 채팅 UI
- 사용자별 세션 히스토리 저장

## 요청 형식

```json
{
  "question": "정책 문서 요약해줘",
  "document_ids": ["doc-1"],
  "top_k": 5
}
```

`document_ids`와 `top_k`는 선택 값입니다. `top_k`가 없으면 `CHAT_RETRIEVAL_LIMIT` 기본값을 사용합니다.

## 응답 형식

```json
{
  "answer": "권한이 확인된 문서 기준 답변입니다. [1]",
  "model": "google/gemma-4-E4B-it",
  "citations": [
    {
      "citation_id": 1,
      "document_id": "doc-1",
      "filename": "policy.md",
      "chunk_index": 0,
      "score": 0.88,
      "snippet": "문서 일부"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 6,
    "total_tokens": 16
  },
  "retrieved_chunk_count": 1
}
```

## 오류 정책

- 검색 컨텍스트가 없으면 `404 CHAT_CONTEXT_NOT_FOUND`를 반환합니다.
- vLLM 호출 실패는 `502 CHAT_LLM_UNAVAILABLE`로 변환합니다.
- API Key 누락 또는 오류는 기존 인증 오류 정책을 따릅니다.

## 후속 작업

다음 단계에서는 BGE Reranker를 검색 결과와 컨텍스트 빌더 사이에 연결하고, 답변 요청/응답을 감사 로그로 남깁니다.
