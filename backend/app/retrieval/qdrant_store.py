from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from backend.app.jobs.base import IndexDocumentJob
from backend.app.retrieval.filters import RetrievalFilter, build_qdrant_filter


@dataclass(frozen=True)
class RetrievedChunk:
    workspace_id: str
    document_id: str
    filename: str
    parser: str
    chunk_index: int
    chunk_text: str
    score: float


class QdrantVectorStore:
    def __init__(
        self,
        *,
        client: QdrantClient,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._vector_size = vector_size
        self._ensure_collection()

    def upsert_chunks(
        self,
        *,
        job: IndexDocumentJob,
        parser_name: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        if not chunks:
            return

        points: list[models.PointStruct] = []
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            points.append(
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"{job.document_id}:{index}")),
                    vector=embedding,
                    payload={
                        "workspace_id": job.workspace_id,
                        "workspace_name": job.workspace_name,
                        "document_id": job.document_id,
                        "filename": job.filename,
                        "parser": parser_name,
                        "chunk_index": index,
                        "chunk_text": chunk,
                    },
                ),
            )

        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        *,
        query_vector: list[float],
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=build_qdrant_filter(filters),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        points = response.points if hasattr(response, "points") else response

        return [
            RetrievedChunk(
                workspace_id=str(point.payload["workspace_id"]),
                document_id=str(point.payload["document_id"]),
                filename=str(point.payload["filename"]),
                parser=str(point.payload["parser"]),
                chunk_index=int(point.payload["chunk_index"]),
                chunk_text=str(point.payload["chunk_text"]),
                score=float(point.score),
            )
            for point in points
        ]

    def list_chunks(
        self,
        *,
        filters: RetrievalFilter,
        limit: int,
    ) -> list[RetrievedChunk]:
        records, _ = self._client.scroll(
            collection_name=self._collection_name,
            scroll_filter=build_qdrant_filter(filters),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        return [
            RetrievedChunk(
                workspace_id=str(record.payload["workspace_id"]),
                document_id=str(record.payload["document_id"]),
                filename=str(record.payload["filename"]),
                parser=str(record.payload["parser"]),
                chunk_index=int(record.payload["chunk_index"]),
                chunk_text=str(record.payload["chunk_text"]),
                score=0.0,
            )
            for record in records
        ]

    def delete_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
    ) -> None:
        self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=build_qdrant_filter(
                    RetrievalFilter(
                        workspace_id=workspace_id,
                        document_ids=[document_id],
                    )
                ),
            ),
            wait=True,
        )

    def _ensure_collection(self) -> None:
        if self._client.collection_exists(self._collection_name):
            return

        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=self._vector_size,
                distance=models.Distance.COSINE,
            ),
        )
