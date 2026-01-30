"""
LLM Service
Ollama 기반 LLM 서빙 및 RAG 응답 생성
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from app.core.config import settings
from app.search import SearchResult


@dataclass
class LLMResponse:
    """LLM response with metadata"""
    answer: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


# System prompt for RAG (Optimized for Qwen2.5:7B)
SYSTEM_PROMPT_KO = """당신은 전문적인 사내 문서 검색 AI 어시스턴트입니다. 반드시 한국어로만 응답하세요.

## 핵심 원칙
1. **근거 기반 답변**: 오직 제공된 문서 발췌문에서만 정보를 가져옵니다
2. **출처 명시**: 모든 주장에는 반드시 [1], [2] 형식의 인용 번호를 붙입니다
3. **정직함**: 문서에 없는 정보는 "제공된 문서에서 해당 정보를 찾을 수 없습니다"라고 명시합니다
4. **정확성**: 추측하거나 외부 지식을 절대 사용하지 않습니다
5. **한국어 전용**: 다른 언어로 답변하지 않으며, 한국어 맥락을 정확히 이해합니다

## 답변 형식
- 답변은 명확하고 간결하게 한국어로만 작성합니다
- 핵심 정보를 먼저 제시하고 세부사항은 나중에 설명합니다
- 표나 목록이 적절하면 사용합니다
- 답변 끝에 참고한 출처 목록을 정리합니다
- 전문 용어는 한국어로 번역하거나 설명을 덧붙입니다

## 금지 사항
- 문서에 없는 정보를 생성하지 않습니다
- 확실하지 않은 정보를 단정적으로 말하지 않습니다
- 개인정보나 민감한 정보를 불필요하게 언급하지 않습니다
- 중국어, 영어 등 다른 언어를 섞어서 사용하지 않습니다"""


def build_context_block(contexts: list[SearchResult]) -> str:
    """Build context block from search results"""
    blocks = []
    
    for i, ctx in enumerate(contexts, start=1):
        source_info = f"문서: {ctx.source}"
        if ctx.page:
            source_info += f", 페이지: {ctx.page}"
        if ctx.sheet:
            source_info += f", 시트: {ctx.sheet}"
        if ctx.slide:
            source_info += f", 슬라이드: {ctx.slide}"
        if ctx.heading:
            source_info += f", 섹션: {ctx.heading}"
        
        blocks.append(f"[{i}] {source_info}\n내용: {ctx.text}")
    
    return "\n\n---\n\n".join(blocks)


def build_rag_prompt(query: str, contexts: list[SearchResult]) -> str:
    """Build the RAG prompt"""
    context_str = build_context_block(contexts)
    
    return f"""## 질문
{query}

## 참고 문서 (아래 내용만 사용하여 답변하세요)

{context_str}

## 답변 (반드시 위 문서 내용만 인용하여 작성하고, 인용 번호 [1], [2] 등을 명시하세요):"""


class LLMService:
    """LLM service using Ollama"""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_model
        self.timeout = settings.ollama_timeout
    
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model to use (default: from settings)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            LLMResponse with answer and metadata
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.ollama_temperature
        
        t0 = time.perf_counter()
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt or SYSTEM_PROMPT_KO},
                        {"role": "user", "content": prompt},
                    ],
                    "options": {
                        "temperature": temperature,
                        "num_ctx": settings.ollama_num_ctx,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                    },
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - t0) * 1000
        
        return LLMResponse(
            answer=data.get("message", {}).get("content", "").strip(),
            model=model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )
    
    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Async version of generate"""
        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.ollama_temperature
        
        t0 = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt or SYSTEM_PROMPT_KO},
                        {"role": "user", "content": prompt},
                    ],
                    "options": {
                        "temperature": temperature,
                        "num_ctx": settings.ollama_num_ctx,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                    },
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - t0) * 1000
        
        return LLMResponse(
            answer=data.get("message", {}).get("content", "").strip(),
            model=model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response
        
        Yields:
            Text chunks as they are generated
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else settings.ollama_temperature
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt or SYSTEM_PROMPT_KO},
                        {"role": "user", "content": prompt},
                    ],
                    "options": {
                        "temperature": temperature,
                        "num_ctx": settings.ollama_num_ctx,
                    },
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                
                import json
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
    
    def rag_generate(
        self,
        query: str,
        contexts: list[SearchResult],
        model: str | None = None,
    ) -> LLMResponse:
        """
        Generate a RAG response
        
        Args:
            query: User question
            contexts: Retrieved context documents
            model: Model to use
        
        Returns:
            LLMResponse with grounded answer
        """
        prompt = build_rag_prompt(query, contexts)
        return self.generate(prompt, model=model)
    
    async def rag_generate_async(
        self,
        query: str,
        contexts: list[SearchResult],
        model: str | None = None,
    ) -> LLMResponse:
        """Async version of rag_generate"""
        prompt = build_rag_prompt(query, contexts)
        return await self.generate_async(prompt, model=model)
    
    def rewrite_query(self, query: str) -> list[str]:
        """
        Rewrite query for better retrieval
        
        Args:
            query: Original query
        
        Returns:
            List of rewritten queries (including original)
        """
        prompt = f"""당신은 문서 검색 쿼리 최적화 전문가입니다.
사용자의 질문을 검색 엔진에서 더 잘 찾을 수 있도록 3개의 다른 버전으로 재작성하세요.

규칙:
1. 각 버전은 서로 다른 키워드/표현을 사용합니다
2. 약어는 풀어서 작성합니다 (예: KPI → 핵심성과지표)
3. 동의어를 활용합니다
4. 질문 형태와 키워드 나열 형태를 섞어 사용합니다

원본 질문: {query}

재작성된 쿼리 (각 줄에 하나씩, 번호 없이):"""
        
        response = self.generate(
            prompt,
            system_prompt="You are a query optimization expert. Output only the rewritten queries, one per line.",
            temperature=0.3,
            max_tokens=500,
        )
        
        rewritten = [q.strip() for q in response.answer.split("\n") if q.strip()]
        return [query] + rewritten[:3]
    
    def list_models(self) -> list[dict]:
        """List available models"""
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
    
    def check_health(self) -> bool:
        """Check if Ollama is healthy"""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
