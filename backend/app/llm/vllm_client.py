from typing import Any

import httpx

from backend.app.llm.base import LLMProviderError, LLMRequest, LLMResponse
from backend.app.llm.profiles import LLMProfile


class VLLMClient:
    def __init__(
        self,
        *,
        profile: LLMProfile,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._profile = profile
        self._http_client = http_client or httpx.Client(timeout=profile.timeout_seconds)

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self._profile.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "max_tokens": request.max_tokens or self._profile.max_tokens,
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self._profile.temperature
            ),
        }

        headers = self._build_headers()
        try:
            response = self._http_client.post(
                f"{self._profile.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._profile.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"vLLM request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"vLLM request failed with HTTP {response.status_code}: "
                f"{_extract_error_message(response)}",
            )

        try:
            response_body = response.json()
        except ValueError as exc:
            raise LLMProviderError("vLLM response was not valid JSON") from exc

        return self._parse_response(response_body)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._profile.api_key:
            headers["Authorization"] = f"Bearer {self._profile.api_key}"
        return headers

    def _parse_response(self, response_body: dict[str, Any]) -> LLMResponse:
        choices = response_body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMProviderError("vLLM response did not include choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMProviderError("vLLM response choices[0] was invalid")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LLMProviderError("vLLM response choices[0].message was invalid")

        content = message.get("content")
        if not isinstance(content, str) or content == "":
            raise LLMProviderError(
                "vLLM response choices[0].message.content was invalid",
            )

        usage = response_body.get("usage")
        if not isinstance(usage, dict):
            usage = {}

        return LLMResponse(
            content=content,
            model=str(response_body.get("model") or self._profile.model),
            finish_reason=_optional_str(first_choice.get("finish_reason")),
            prompt_tokens=_optional_int(usage.get("prompt_tokens")),
            completion_tokens=_optional_int(usage.get("completion_tokens")),
            total_tokens=_optional_int(usage.get("total_tokens")),
        )


def _extract_error_message(response: httpx.Response) -> str:
    try:
        response_body = response.json()
    except ValueError:
        return response.text

    if isinstance(response_body, dict):
        error = response_body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        if isinstance(error, str):
            return error

    return response.text


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None
