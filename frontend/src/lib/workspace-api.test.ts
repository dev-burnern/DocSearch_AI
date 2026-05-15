import { describe, expect, it } from "vitest";

import { WorkspaceApiError, createWorkspaceApiClient } from "./workspace-api";

describe("workspace-api", () => {
  it("API Key로 워크스페이스 컨텍스트를 조회한다", async () => {
    const calls: Array<{ input: string; init: RequestInit }> = [];
    const client = createWorkspaceApiClient({
      baseUrl: "/api",
      fetcher: async (input, init) => {
        calls.push({ input, init });
        return new Response(
          JSON.stringify({
            request_id: "req_1",
            workspace_id: "workspace-alpha",
            workspace_name: "Workspace Alpha",
            role: "admin",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      },
    });

    const result = await client.getWorkspace({ apiKey: "admin-key" });

    expect(result).toEqual({
      request_id: "req_1",
      workspace_id: "workspace-alpha",
      workspace_name: "Workspace Alpha",
      role: "admin",
    });
    expect(calls).toHaveLength(1);
    expect(calls[0]).toMatchObject({
      input: "/api/v1/workspace",
      init: {
        method: "GET",
        headers: {
          "X-API-Key": "admin-key",
        },
      },
    });
  });

  it("오류 응답 메시지를 예외로 변환한다", async () => {
    const client = createWorkspaceApiClient({
      fetcher: async () =>
        new Response(
          JSON.stringify({
            detail: {
              code: "AUTH_INVALID_API_KEY",
              message: "API key is invalid.",
            },
          }),
          {
            status: 401,
            headers: { "Content-Type": "application/json" },
          },
        ),
    });

    await expect(client.getWorkspace({ apiKey: "bad-key" })).rejects.toThrow(
      new WorkspaceApiError("API key is invalid."),
    );
  });
});
