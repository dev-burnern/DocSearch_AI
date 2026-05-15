import { describe, expect, it, vi } from "vitest";

import { createOperationsApiClient } from "./operations-api";

describe("createOperationsApiClient", () => {
  it("운영 상태 API를 공통 API Key 헤더로 호출한다", async () => {
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
          checks: [
            {
              name: "configuration",
              status: "ready",
              message: "운영 설정 기준을 통과했습니다.",
            },
          ],
          settings: {
            environment: "development",
            debug: false,
            dependency_health_checks_enabled: true,
            dependency_health_timeout_seconds: 2,
            rate_limit: {
              enabled: true,
              requests: 120,
              window_seconds: 60,
              backend: "redis",
              fail_open: true,
            },
            backends: {
              audit_log: "postgres",
              document_metadata: "postgres",
              indexing_queue: "inprocess",
              reranker: "score",
            },
            models: {
              llm: "google/gemma-4-E4B-it",
              reranker: "BAAI/bge-reranker-v2-m3",
              embedding_vector_size: 8,
            },
          },
        }),
        { status: 200 },
      ),
    );
    const client = createOperationsApiClient({
      baseUrl: "http://localhost:8000",
      fetcher,
    });

    const response = await client.getOperationsStatus({ apiKey: "admin-key" });

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/admin/operations",
      {
        method: "GET",
        headers: {
          "X-API-Key": "admin-key",
        },
      },
    );
    expect(response.status).toBe("ready");
    expect(response.settings.rate_limit.requests).toBe(120);
    expect(response.settings.rate_limit.backend).toBe("redis");
    expect(response.settings.rate_limit.fail_open).toBe(true);
  });

  it("오류 응답의 메시지를 예외로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "AUTH_FORBIDDEN_ROLE",
            message: "Admin role is required.",
          },
        }),
        { status: 403 },
      ),
    );
    const client = createOperationsApiClient({ fetcher });

    await expect(
      client.getOperationsStatus({ apiKey: "member-key" }),
    ).rejects.toThrow("Admin role is required.");
  });
});
