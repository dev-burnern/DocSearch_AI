from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.core.config import Settings
from backend.app.documents.router import (
    get_embedder,
    get_qdrant_store,
    get_runtime_settings,
)
from backend.app.documents.security import (
    DocumentSecurityPermissionError,
    filter_document_security_levels_for_role,
)
from backend.app.indexing.embedder import EmbeddingProviderError
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.retriever import Retriever, build_retriever
from backend.app.search.models import SearchRequest, SearchResponse, SearchResultChunk


router = APIRouter(prefix="/v1/search", tags=["search"])


def get_search_retriever(
    embedder=Depends(get_embedder),
    vector_store=Depends(get_qdrant_store),
    settings: Settings = Depends(get_runtime_settings),
) -> Retriever:
    return build_retriever(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
    )


@router.post("", response_model=SearchResponse)
async def search_documents(
    search_request: SearchRequest,
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    retriever: Retriever = Depends(get_search_retriever),
) -> SearchResponse:
    try:
        security_levels = filter_document_security_levels_for_role(
            role=workspace_context.role,
            requested_security_levels=search_request.security_levels,
        )
    except DocumentSecurityPermissionError as exc:
        raise _document_security_forbidden() from exc

    try:
        chunks = retriever.retrieve(
            query_text=search_request.query,
            filters=RetrievalFilter(
                workspace_id=workspace_context.workspace_id,
                document_ids=search_request.document_ids,
                security_levels=security_levels,
            ),
            limit=search_request.limit,
        )
    except EmbeddingProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "SEARCH_EMBEDDING_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc

    results = [
        SearchResultChunk(
            document_id=chunk.document_id,
            filename=chunk.filename,
            parser=chunk.parser,
            security_level=chunk.security_level,
            chunk_index=chunk.chunk_index,
            score=chunk.score,
            snippet=chunk.chunk_text,
        )
        for chunk in chunks
    ]

    return SearchResponse(
        query=search_request.query,
        total=len(results),
        results=results,
    )


def _document_security_forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "DOCUMENT_SECURITY_FORBIDDEN",
            "message": "Document security level is not allowed for this role.",
        },
    )
