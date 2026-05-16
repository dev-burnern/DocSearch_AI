import { describe, expect, it, vi } from "vitest";

import { createChatApiClient } from "./chat-api";

describe("createChatApiClient", () => {
  it("Bearer 토큰과 질문 요청을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          answer: "문서 기반 답변입니다. [1]",
          model: "local-model",
          citations: [],
          usage: {},
          retrieved_chunk_count: 0,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createChatApiClient({ baseUrl: "http://api.local", fetcher });

    const response = await client.ask({
      authToken: "auth-token",
      question: "정책 요약해줘",
      documentIds: ["doc-1"],
      securityLevels: ["restricted"],
      topK: 5,
    });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer auth-token",
      },
      body: JSON.stringify({
        question: "정책 요약해줘",
        document_ids: ["doc-1"],
        security_levels: ["restricted"],
        top_k: 5,
      }),
    });
    expect(response.answer).toBe("문서 기반 답변입니다. [1]");
  });

  it("API 오류 메시지를 예외로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: { code: "AUTH_INVALID_TOKEN", message: "토큰이 올바르지 않습니다." },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createChatApiClient({ baseUrl: "", fetcher });

    await expect(
      client.ask({
        authToken: "bad-token",
        question: "질문",
        documentIds: [],
        securityLevels: [],
        topK: 5,
      }),
    ).rejects.toThrow("토큰이 올바르지 않습니다.");
  });
});
