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
});
