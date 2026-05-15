import { describe, expect, it, vi } from "vitest";

import { createAuditLogApiClient } from "./audit-log-api";

describe("createAuditLogApiClient", () => {
  it("채팅 감사 로그 API에 API Key를 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total: 0, events: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createAuditLogApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const response = await client.listChatEvents({
      apiKey: "local-dev-key",
    });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/audit-logs/chat", {
      method: "GET",
      headers: {
        "X-API-Key": "local-dev-key",
      },
    });
    expect(response.total).toBe(0);
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
    const client = createAuditLogApiClient({
      baseUrl: "",
      fetcher,
    });

    await expect(
      client.listChatEvents({ apiKey: "bad-key" }),
    ).rejects.toThrow("API key is invalid.");
  });

  it("선택한 감사 로그 필터를 쿼리 문자열로 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total: 0, events: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createAuditLogApiClient({
      baseUrl: "http://api.local/",
      fetcher,
    });

    await client.listChatEvents({
      apiKey: "local-dev-key",
      query: "정책",
      documentId: "doc-1",
      requestId: "request-1",
      occurredFrom: "2026-05-15T09:00",
      occurredTo: "2026-05-15T10:00",
      limit: 20,
    });

    const requestedUrl = new URL(fetcher.mock.calls[0][0]);
    expect(requestedUrl.origin + requestedUrl.pathname).toBe(
      "http://api.local/v1/audit-logs/chat",
    );
    expect(requestedUrl.searchParams.get("query")).toBe("정책");
    expect(requestedUrl.searchParams.get("document_id")).toBe("doc-1");
    expect(requestedUrl.searchParams.get("request_id")).toBe("request-1");
    expect(requestedUrl.searchParams.get("from")).toBe("2026-05-15T09:00");
    expect(requestedUrl.searchParams.get("to")).toBe("2026-05-15T10:00");
    expect(requestedUrl.searchParams.get("limit")).toBe("20");
  });

  it("채팅 감사 로그 CSV 내보내기 API를 호출하고 파일 정보를 반환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response("이벤트 ID,질문\r\nevent-1,정책 질문\r\n", {
        status: 200,
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition":
            'attachment; filename="chat-audit-logs-20260515.csv"',
        },
      }),
    );
    const client = createAuditLogApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const response = await client.exportChatEvents({
      apiKey: "local-dev-key",
      query: "정책",
      documentId: "doc-1",
      limit: 20,
    });

    const requestedUrl = new URL(fetcher.mock.calls[0][0]);
    expect(requestedUrl.origin + requestedUrl.pathname).toBe(
      "http://api.local/v1/audit-logs/chat/export",
    );
    expect(requestedUrl.searchParams.get("query")).toBe("정책");
    expect(requestedUrl.searchParams.get("document_id")).toBe("doc-1");
    expect(requestedUrl.searchParams.get("limit")).toBe("20");
    expect(fetcher.mock.calls[0][1]).toEqual({
      method: "GET",
      headers: {
        "X-API-Key": "local-dev-key",
      },
    });
    expect(response).toEqual({
      filename: "chat-audit-logs-20260515.csv",
      content: "이벤트 ID,질문\r\nevent-1,정책 질문\r\n",
      contentType: "text/csv; charset=utf-8",
    });
  });
});
