import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OperationsStatusWorkspace } from "./OperationsStatusWorkspace";

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
    expect(screen.getByText("qdrant")).toBeInTheDocument();
    expect(screen.getByText("Qdrant 연결이 정상입니다.")).toBeInTheDocument();
    expect(screen.getByText("google/gemma-4-E4B-it")).toBeInTheDocument();
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

function buildOperationsResponse() {
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
    settings: {
      environment: "development",
      debug: false,
      dependency_health_checks_enabled: true,
      dependency_health_timeout_seconds: 2,
      rate_limit: {
        enabled: true,
        requests: 120,
        window_seconds: 60,
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
  };
}
