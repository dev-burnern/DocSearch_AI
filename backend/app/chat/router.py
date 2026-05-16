from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.audit.router import get_audit_log_store
from backend.app.audit.store import AuditLogStore
from backend.app.auth.dependencies import require_workspace_context
from backend.app.auth.models import WorkspaceContext
from backend.app.chat.models import ChatRequest, ChatResponse
from backend.app.chat.service import ChatContextNotFoundError, ChatService
from backend.app.core.config import Settings
from backend.app.documents.router import (
    get_embedder,
    get_qdrant_store,
    get_runtime_settings,
)
from backend.app.documents.security import validate_document_security_levels
from backend.app.indexing.embedder import EmbeddingProviderError
from backend.app.llm.base import LLMClient, LLMProviderError
from backend.app.llm.profiles import get_default_llm_profile
from backend.app.llm.vllm_client import VLLMClient
from backend.app.reranking.base import Reranker, RerankerProviderError, ScorePreservingReranker
from backend.app.reranking.bge_client import BGERerankerClient
from backend.app.reranking.profiles import get_default_reranker_profile
from backend.app.retrieval.retriever import Retriever, build_retriever


router = APIRouter(prefix="/v1/chat", tags=["chat"])


def get_retriever(
    embedder=Depends(get_embedder),
    vector_store=Depends(get_qdrant_store),
    settings: Settings = Depends(get_runtime_settings),
) -> Retriever:
    return build_retriever(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
    )


def get_llm_client(
    settings: Settings = Depends(get_runtime_settings),
) -> LLMClient:
    return VLLMClient(profile=get_default_llm_profile(settings))


def get_reranker(
    settings: Settings = Depends(get_runtime_settings),
) -> Reranker:
    if settings.reranker_backend == "bge":
        return BGERerankerClient(profile=get_default_reranker_profile(settings))
    return ScorePreservingReranker()


def get_chat_service(
    retriever: Retriever = Depends(get_retriever),
    reranker: Reranker = Depends(get_reranker),
    llm_client: LLMClient = Depends(get_llm_client),
    audit_log: AuditLogStore = Depends(get_audit_log_store),
    settings: Settings = Depends(get_runtime_settings),
) -> ChatService:
    return ChatService(
        retriever=retriever,
        reranker=reranker,
        llm_client=llm_client,
        audit_log=audit_log,
        retrieval_limit=settings.chat_retrieval_limit,
        rerank_top_k=settings.chat_rerank_top_k,
        min_relevance_score=settings.chat_min_relevance_score,
    )


@router.post("", response_model=ChatResponse, response_model_exclude_none=True)
async def answer_question(
    chat_request: ChatRequest,
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        validated_request = chat_request.model_copy(
            update={
                "security_levels": validate_document_security_levels(
                    chat_request.security_levels,
                ),
            },
        )
        return chat_service.answer(
            workspace_context=workspace_context,
            chat_request=validated_request,
        )
    except ChatContextNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CHAT_CONTEXT_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    except EmbeddingProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "CHAT_EMBEDDING_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "CHAT_LLM_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
    except RerankerProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "CHAT_RERANKER_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
