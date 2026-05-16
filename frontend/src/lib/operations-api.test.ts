import { describe, expect, it, vi } from "vitest";

import { createOperationsApiClient } from "./operations-api";

describe("createOperationsApiClient", () => {
  it("운영 상태 API에 Bearer 토큰을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ready",
          service: "docsearch-ai",
          workspace: {
            workspace_id: "workspace-alpha",
            workspace_name: "Workspace Alpha",
            role: "admin",
          },
          checks: [],
          events: [],
          settings: {},
          indexing_queue: {},
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createOperationsApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    await client.getOperationsStatus({ authToken: "auth-token" });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/admin/operations", {
      method: "GET",
      headers: { Authorization: "Bearer auth-token" },
    });
  });

  it("API 오류 메시지를 예외로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { message: "Admin role is required." } }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createOperationsApiClient({ baseUrl: "", fetcher });

    await expect(
      client.getOperationsStatus({ authToken: "member-token" }),
    ).rejects.toThrow("Admin role is required.");
  });
});
