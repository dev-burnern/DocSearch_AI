import { describe, expect, it, vi } from "vitest";

import { createSearchApiClient } from "./search-api";

describe("createSearchApiClient", () => {
  it("검색 API에 API Key와 검색 조건을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "권한 정책",
          total: 1,
          results: [
            {
              document_id: "doc-1",
              filename: "policy.md",
              parser: "markdown",
              chunk_index: 2,
              score: 0.87,
              snippet: "권한 정책 문서 일부",
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createSearchApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const response = await client.searchDocuments({
      apiKey: "local-dev-key",
      query: "권한 정책",
      documentIds: ["doc-1"],
      limit: 5,
    });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": "local-dev-key",
      },
      body: JSON.stringify({
        query: "권한 정책",
        document_ids: ["doc-1"],
        limit: 5,
      }),
    });
    expect(response.total).toBe(1);
  });

  it("검색 API 오류 메시지를 사용자에게 전달할 수 있는 오류로 변환한다", async () => {
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
    const client = createSearchApiClient({
      baseUrl: "",
      fetcher,
    });

    await expect(
      client.searchDocuments({
        apiKey: "bad-key",
        query: "권한 정책",
        documentIds: [],
        limit: 5,
      }),
    ).rejects.toThrow("API key is invalid.");
  });
});
