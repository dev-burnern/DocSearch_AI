import { describe, expect, it, vi } from "vitest";

import { createChatApiClient } from "./chat-api";

describe("createChatApiClient", () => {
  it("채팅 API에 API Key와 질문 요청을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          answer: "문서 기준 답변입니다. [1]",
          model: "google/gemma-4-E4B-it",
          citations: [],
          usage: {},
          retrieved_chunk_count: 0,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createChatApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const response = await client.ask({
      apiKey: "local-dev-key",
      question: "정책 문서 요약해줘",
      documentIds: ["doc-1"],
      topK: 5,
    });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": "local-dev-key",
      },
      body: JSON.stringify({
        question: "정책 문서 요약해줘",
        document_ids: ["doc-1"],
        top_k: 5,
      }),
    });
    expect(response.answer).toBe("문서 기준 답변입니다. [1]");
  });

  it("API 오류 메시지를 사용자에게 전달할 수 있는 오류로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "AUTH_INVALID_API_KEY",
            message: "API key is invalid.",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createChatApiClient({
      baseUrl: "",
      fetcher,
    });

    await expect(
      client.ask({
        apiKey: "bad-key",
        question: "질문",
        documentIds: [],
        topK: 5,
      }),
    ).rejects.toThrow("API key is invalid.");
  });
});
