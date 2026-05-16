import { describe, expect, it, vi } from "vitest";

import { createAuditLogApiClient } from "./audit-log-api";

describe("createAuditLogApiClient", () => {
  it("감사 로그 조회에 Bearer 토큰과 필터를 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ events: [], total: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createAuditLogApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    await client.listChatEvents({
      authToken: "auth-token",
      query: "정책",
      documentId: "doc-1",
      requestId: "req-1",
      limit: 20,
    });

    const requestedUrl = new URL(fetcher.mock.calls[0][0]);
    expect(requestedUrl.pathname).toBe("/v1/audit-logs/chat");
    expect(requestedUrl.searchParams.get("query")).toBe("정책");
    expect(requestedUrl.searchParams.get("document_id")).toBe("doc-1");
    expect(fetcher.mock.calls[0][1]).toEqual({
      method: "GET",
      headers: { Authorization: "Bearer auth-token" },
    });
  });

  it("감사 로그 CSV 내보내기 결과를 파일 정보로 반환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response("event_id\n1\n", {
        status: 200,
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition": 'attachment; filename="chat.csv"',
        },
      }),
    );
    const client = createAuditLogApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const file = await client.exportChatEvents({
      authToken: "auth-token",
      documentId: "doc-1",
    });

    expect(fetcher.mock.calls[0][1]).toEqual({
      method: "GET",
      headers: { Authorization: "Bearer auth-token" },
    });
    expect(file).toEqual({
      filename: "chat.csv",
      content: "event_id\n1\n",
      contentType: "text/csv; charset=utf-8",
    });
  });
});
