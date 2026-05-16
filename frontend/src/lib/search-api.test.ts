import { describe, expect, it, vi } from "vitest";

import { createSearchApiClient } from "./search-api";

describe("createSearchApiClient", () => {
  it("Bearer 토큰과 검색 조건을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ query: "권한", total: 0, results: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createSearchApiClient({ baseUrl: "http://api.local", fetcher });

    await client.searchDocuments({
      authToken: "auth-token",
      query: "권한",
      documentIds: ["doc-1"],
      securityLevels: ["internal"],
      limit: 5,
    });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer auth-token",
      },
      body: JSON.stringify({
        query: "권한",
        document_ids: ["doc-1"],
        security_levels: ["internal"],
        limit: 5,
      }),
    });
  });

  it("API 오류 메시지를 예외로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { message: "검색 실패" } }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createSearchApiClient({ baseUrl: "", fetcher });

    await expect(
      client.searchDocuments({
        authToken: "bad-token",
        query: "권한",
        documentIds: [],
        securityLevels: [],
        limit: 5,
      }),
    ).rejects.toThrow("검색 실패");
  });
});
