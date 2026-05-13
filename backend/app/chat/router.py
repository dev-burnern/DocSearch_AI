from fastapi import APIRouter, Depends, HTTPException, status

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
from backend.app.llm.base import LLMClient, LLMProviderError
from backend.app.llm.profiles import get_default_llm_profile
from backend.app.llm.vllm_client import VLLMClient
from backend.app.retrieval.retriever import DenseRetriever


router = APIRouter(prefix="/v1/chat", tags=["chat"])


def get_retriever(
    embedder=Depends(get_embedder),
    vector_store=Depends(get_qdrant_store),
) -> DenseRetriever:
    return DenseRetriever(embedder=embedder, vector_store=vector_store)


def get_llm_client(
    settings: Settings = Depends(get_runtime_settings),
) -> LLMClient:
    return VLLMClient(profile=get_default_llm_profile(settings))


def get_chat_service(
    retriever: DenseRetriever = Depends(get_retriever),
    llm_client: LLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_runtime_settings),
) -> ChatService:
    return ChatService(
        retriever=retriever,
        llm_client=llm_client,
        retrieval_limit=settings.chat_retrieval_limit,
    )


@router.post("", response_model=ChatResponse)
async def answer_question(
    chat_request: ChatRequest,
    workspace_context: WorkspaceContext = Depends(require_workspace_context),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return chat_service.answer(
            workspace_context=workspace_context,
            chat_request=chat_request,
        )
    except ChatContextNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CHAT_CONTEXT_NOT_FOUND",
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
