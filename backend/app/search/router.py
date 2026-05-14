from fastapi import APIRouter, Depends

from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.documents.router import get_embedder, get_qdrant_store
from backend.app.retrieval.filters import RetrievalFilter
from backend.app.retrieval.retriever import DenseRetriever
from backend.app.search.models import SearchRequest, SearchResponse, SearchResultChunk


router = APIRouter(prefix="/v1/search", tags=["search"])


def get_search_retriever(
    embedder=Depends(get_embedder),
    vector_store=Depends(get_qdrant_store),
) -> DenseRetriever:
    return DenseRetriever(embedder=embedder, vector_store=vector_store)


@router.post("", response_model=SearchResponse)
async def search_documents(
    search_request: SearchRequest,
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    retriever: DenseRetriever = Depends(get_search_retriever),
) -> SearchResponse:
    chunks = retriever.retrieve(
        query_text=search_request.query,
        filters=RetrievalFilter(
            workspace_id=workspace_context.workspace_id,
            document_ids=search_request.document_ids,
        ),
        limit=search_request.limit,
    )

    results = [
        SearchResultChunk(
            document_id=chunk.document_id,
            filename=chunk.filename,
            parser=chunk.parser,
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
