import { describe, expect, it, vi } from "vitest";

import { createWorkspaceApiClient } from "./workspace-api";

describe("createWorkspaceApiClient", () => {
  it("Bearer 토큰으로 워크스페이스 컨텍스트를 조회한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          request_id: "req-1",
          workspace_id: "workspace-alpha",
          workspace_name: "Workspace Alpha",
          role: "admin",
          employee_id: "1001",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createWorkspaceApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const result = await client.getWorkspace({ authToken: "auth-token" });

    expect(fetcher).toHaveBeenCalledWith("http://api.local/v1/workspace", {
      method: "GET",
      headers: { Authorization: "Bearer auth-token" },
    });
    expect(result.employee_id).toBe("1001");
  });

  it("API 오류 메시지를 예외로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { message: "로그인이 필요합니다." } }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createWorkspaceApiClient({ baseUrl: "", fetcher });

    await expect(
      client.getWorkspace({ authToken: "bad-token" }),
    ).rejects.toThrow("로그인이 필요합니다.");
  });
});
