import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OperationsStatusWorkspace } from "./OperationsStatusWorkspace";
import type { OperationsStatusResponse } from "../../lib/operations-api";

describe("OperationsStatusWorkspace", () => {
  it("운영 상태를 조회하고 요약 정보를 표시한다", async () => {
    const user = userEvent.setup();
    const client = {
      getOperationsStatus: vi.fn().mockResolvedValue(buildOperationsResponse()),
    };

    render(<OperationsStatusWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "admin-key");
    await user.click(screen.getByRole("button", { name: /상태 새로고침/ }));

    await waitFor(() => {
      expect(client.getOperationsStatus).toHaveBeenCalledWith({
        apiKey: "admin-key",
      });
    });
    expect(await screen.findAllByText("ready")).toHaveLength(3);
    expect(screen.getByText("Workspace Alpha")).toBeInTheDocument();
    expect(screen.getByText("development")).toBeInTheDocument();
    expect(screen.getByText("rate limit 120/60s")).toBeInTheDocument();
    expect(screen.getByText("rate backend redis")).toBeInTheDocument();
    expect(screen.getByText("fail-open on")).toBeInTheDocument();
    expect(screen.getByText("retrieval hybrid")).toBeInTheDocument();
    expect(screen.getByText("hybrid 0.7/0.3")).toBeInTheDocument();
    expect(screen.getByText("indexing queue ready")).toBeInTheDocument();
    expect(screen.getByText("pending 3")).toBeInTheDocument();
    expect(screen.getByText("max attempts 5")).toBeInTheDocument();
    expect(screen.getByText("docsearch:indexing:queue")).toBeInTheDocument();
    expect(screen.getByText("qdrant")).toBeInTheDocument();
    expect(screen.getByText("Qdrant 연결이 정상입니다.")).toBeInTheDocument();
    expect(screen.getByText("기록된 운영 이벤트가 없습니다.")).toBeInTheDocument();
    expect(screen.getByText("google/gemma-4-E4B-it")).toBeInTheDocument();
    expect(screen.getByText("embedding backend deterministic")).toBeInTheDocument();
    expect(screen.getByText("BAAI/bge-m3")).toBeInTheDocument();
    expect(
      screen.getByText("Redis 인덱싱 큐 대기건수 조회에 성공했습니다."),
    ).toBeInTheDocument();
  });

  it("운영 이벤트를 표시한다", async () => {
    const user = userEvent.setup();
    const client = {
      getOperationsStatus: vi.fn().mockResolvedValue(
        buildOperationsResponse({
          events: [
            {
              event_id: "event-1",
              event_type: "dependency.health_failed",
              severity: "error" as const,
              source: "qdrant",
              message: "Qdrant 연결에 실패했습니다.",
              occurred_at: "2026-05-16T00:00:00Z",
              details: { check: "qdrant" },
            },
          ],
        }),
      ),
    };

    render(<OperationsStatusWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "admin-key");
    await user.click(screen.getByRole("button", { name: /상태 새로고침/ }));

    expect(await screen.findByText("운영 이벤트")).toBeInTheDocument();
    expect(screen.getByText("dependency.health_failed")).toBeInTheDocument();
    expect(screen.getByText("Qdrant 연결에 실패했습니다.")).toBeInTheDocument();
  });

  it("공통 API Key를 받으면 내부 API Key 입력을 숨기고 그대로 사용한다", async () => {
    const user = userEvent.setup();
    const client = {
      getOperationsStatus: vi.fn().mockResolvedValue(buildOperationsResponse()),
    };

    render(<OperationsStatusWorkspace apiKey="admin-key" client={client} />);

    expect(screen.queryByLabelText("API Key")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /상태 새로고침/ }));

    await waitFor(() => {
      expect(client.getOperationsStatus).toHaveBeenCalledWith({
        apiKey: "admin-key",
      });
    });
  });

  it("조회 실패 메시지를 보여준다", async () => {
    const user = userEvent.setup();
    const client = {
      getOperationsStatus: vi
        .fn()
        .mockRejectedValue(new Error("Admin role is required.")),
    };

    render(<OperationsStatusWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "member-key");
    await user.click(screen.getByRole("button", { name: /상태 새로고침/ }));

    expect(await screen.findByText("Admin role is required.")).toBeInTheDocument();
  });
});

function buildOperationsResponse(
  overrides: Partial<OperationsStatusResponse> = {},
): OperationsStatusResponse {
  return {
    ...buildBaseOperationsResponse(),
    ...overrides,
  };
}

function buildBaseOperationsResponse(): OperationsStatusResponse {
  return {
    status: "ready" as const,
    service: "docsearch-ai",
    workspace: {
      workspace_id: "workspace-alpha",
      workspace_name: "Workspace Alpha",
      role: "admin" as const,
    },
    checks: [
      {
        name: "configuration",
        status: "ready" as const,
        message: "운영 설정 기준을 통과했습니다.",
      },
      {
        name: "qdrant",
        status: "ready" as const,
        message: "Qdrant 연결이 정상입니다.",
      },
    ],
    events: [],
    indexing_queue: {
      backend: "redis",
      status: "ready" as const,
      queue_key: "docsearch:indexing:queue",
      pending_jobs: 3,
      max_attempts: 5,
      message: "Redis 인덱싱 큐 대기건수 조회에 성공했습니다.",
    },
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
        requests: 120,
        window_seconds: 60,
        backend: "redis",
        fail_open: true,
      },
      backends: {
        audit_log: "postgres",
        document_metadata: "postgres",
        indexing_queue: "inprocess",
        embedding: "deterministic",
        reranker: "score",
      },
      models: {
        llm: "google/gemma-4-E4B-it",
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
  };
}
