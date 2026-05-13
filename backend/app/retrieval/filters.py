from dataclasses import dataclass

from qdrant_client import models


@dataclass(frozen=True)
class RetrievalFilter:
    workspace_id: str
    document_ids: list[str] | None = None


def build_qdrant_filter(filters: RetrievalFilter) -> models.Filter:
    must = [
        models.FieldCondition(
            key="workspace_id",
            match=models.MatchValue(value=filters.workspace_id),
        ),
    ]
    should = None

    if filters.document_ids:
        should = [
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(value=document_id),
            )
            for document_id in filters.document_ids
        ]

    return models.Filter(must=must, should=should)
