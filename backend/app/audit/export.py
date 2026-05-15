import csv
from datetime import UTC, datetime
from io import StringIO

from backend.app.audit.models import ChatAuditEvent


CSV_FIELDNAMES = [
    "이벤트 ID",
    "발생 시각",
    "이벤트 유형",
    "워크스페이스 ID",
    "워크스페이스 이름",
    "요청 ID",
    "질문",
    "답변 미리보기",
    "문서 ID",
    "출처 파일",
    "검색 제한",
    "리랭크 상위 K",
    "검색 청크 수",
    "모델",
    "프롬프트 토큰",
    "완료 토큰",
    "전체 토큰",
]


def build_chat_audit_csv(events: list[ChatAuditEvent]) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()

    for event in events:
        writer.writerow(
            {
                "이벤트 ID": event.event_id,
                "발생 시각": _format_utc(event.occurred_at),
                "이벤트 유형": event.event_type,
                "워크스페이스 ID": event.workspace_id,
                "워크스페이스 이름": event.workspace_name,
                "요청 ID": event.request_id,
                "질문": event.question,
                "답변 미리보기": event.answer_preview,
                "문서 ID": _join_values(event.document_ids or []),
                "출처 파일": _join_values(
                    [citation.filename for citation in event.citations],
                ),
                "검색 제한": event.retrieval_limit,
                "리랭크 상위 K": event.rerank_top_k,
                "검색 청크 수": event.retrieved_chunk_count,
                "모델": event.model,
                "프롬프트 토큰": _optional_number(event.prompt_tokens),
                "완료 토큰": _optional_number(event.completion_tokens),
                "전체 토큰": _optional_number(event.total_tokens),
            }
        )

    return output.getvalue()


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _join_values(values: list[str]) -> str:
    return "; ".join(values)


def _optional_number(value: int | None) -> int | str:
    return value if value is not None else ""
