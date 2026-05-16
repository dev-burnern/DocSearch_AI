import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { OperationsStatusResponse } from "../../lib/operations-api";
import { OperationsStatusWorkspace } from "./OperationsStatusWorkspace";

describe("OperationsStatusWorkspace", () => {
  it("운영 상태를 조회하고 요약 정보를 표시한다", async () => {
    const user = userEvent.setup();
    const client = {
      getOperationsStatus: vi.fn().mockResolvedValue(buildOperationsResponse()),
    };

    render(<OperationsStatusWorkspace authToken="auth-token" client={client} />);

    await user.click(screen.getByRole("button", { name: /상태 새로고침/ }));

    await waitFor(() => {
      expect(client.getOperationsStatus).toHaveBeenCalledWith({
        authToken: "auth-token",
      });
    });
    expect(await screen.findByText("Workspace Alpha")).toBeInTheDocument();
    expect(screen.getByText("rate limit 120/60s")).toBeInTheDocument();
    expect(screen.getByText("indexing queue ready")).toBeInTheDocument();
  });

  it("조회 실패 메시지를 보여준다", async () => {
    const user = userEvent.setup();
    const client = {
      getOperationsStatus: vi
        .fn()
        .mockRejectedValue(new Error("Admin role is required.")),
    };

    render(<OperationsStatusWorkspace authToken="auth-token" client={client} />);

    await user.click(screen.getByRole("button", { name: /상태 새로고침/ }));

    expect(await screen.findByText("Admin role is required.")).toBeInTheDocument();
  });
});

function buildOperationsResponse(): OperationsStatusResponse {
  return {
    status: "ready",
    service: "docsearch-ai",
    workspace: {
      workspace_id: "workspace-alpha",
      workspace_name: "Workspace Alpha",
      role: "admin",
    },
    checks: [
      {
        name: "qdrant",
        status: "ready",
        message: "Qdrant 연결이 정상입니다.",
      },
    ],
    events: [],
    settings: {
      environment: "development",
      debug: false,
      dependency_health_checks_enabled: true,
      dependency_health_timeout_seconds: 2,
      retrieval_mode: "hybrid",
      hybrid_dense_weight: 0.7,
      hybrid_lexical_weight: 0.3,
      hybrid_candidate_limit: 50,
      rate_limit: {
        enabled: true,
        backend: "redis",
        requests: 120,
        window_seconds: 60,
        fail_open: true,
      },
      backends: {
        audit_log: "postgres",
        document_metadata: "postgres",
        indexing_queue: "redis",
        embedding: "deterministic",
        reranker: "score",
      },
      models: {
        llm: "local-model",
        llm_timeout_seconds: 30,
        llm_max_tokens: 1024,
        llm_temperature: 0.2,
        llm_max_retries: 2,
        llm_retry_backoff_seconds: 0.5,
        embedding: "BAAI/bge-m3",
        reranker: "BAAI/bge-reranker-v2-m3",
        embedding_vector_size: 8,
      },
    },
    indexing_queue: {
      backend: "redis",
      status: "ready",
      queue_key: "docsearch:indexing:queue",
      pending_jobs: 3,
      max_attempts: 5,
      message: "Redis 인덱싱 큐 대기건수 조회에 성공했습니다.",
    },
  };
}
