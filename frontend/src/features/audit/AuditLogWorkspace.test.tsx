import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AuditLogWorkspace } from "./AuditLogWorkspace";

describe("AuditLogWorkspace", () => {
  it("API Key로 채팅 감사 로그를 조회하고 이벤트를 표시한다", async () => {
    const user = userEvent.setup();
    const client = {
      listChatEvents: vi.fn().mockResolvedValue({
        total: 1,
        events: [
          {
            event_id: "event-1",
            event_type: "chat.answer.generated",
            occurred_at: "2026-05-14T01:00:00Z",
            request_id: "request-1",
            workspace_id: "workspace-alpha",
            workspace_name: "Workspace Alpha",
            question: "정책 문서 요약해줘",
            document_ids: ["doc-1"],
            retrieval_limit: 5,
            rerank_top_k: 5,
            retrieved_chunk_count: 1,
            model: "google/gemma-4-E4B-it",
            answer_preview: "권한이 허용된 문서 기준으로 답변합니다.",
            answer_character_count: 23,
            prompt_tokens: 10,
            completion_tokens: 6,
            total_tokens: 16,
            citations: [
              {
                citation_id: 1,
                document_id: "doc-1",
                filename: "policy.md",
                chunk_index: 0,
                score: 0.88,
                rerank_score: 0.94,
              },
            ],
          },
        ],
      }),
    };

    render(<AuditLogWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    const submit = screen.getByRole("button", { name: /로그 조회/ });

    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() => {
      expect(client.listChatEvents).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
      });
    });

    expect(await screen.findByText("정책 문서 요약해줘")).toBeInTheDocument();
    expect(
      screen.getByText("권한이 허용된 문서 기준으로 답변합니다."),
    ).toBeInTheDocument();
    expect(screen.getByText("policy.md")).toBeInTheDocument();
    expect(screen.getByText("Workspace Alpha")).toBeInTheDocument();
    expect(screen.getByText("tokens 16")).toBeInTheDocument();
  });

  it("조회 결과가 비어 있으면 빈 상태를 보여준다", async () => {
    const user = userEvent.setup();
    const client = {
      listChatEvents: vi.fn().mockResolvedValue({ total: 0, events: [] }),
    };

    render(<AuditLogWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.click(screen.getByRole("button", { name: /로그 조회/ }));

    expect(await screen.findByText("아직 감사 로그가 없습니다.")).toBeInTheDocument();
  });

  it("조회 실패 메시지를 보여준다", async () => {
    const user = userEvent.setup();
    const client = {
      listChatEvents: vi.fn().mockRejectedValue(new Error("API key is invalid.")),
    };

    render(<AuditLogWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "bad-key");
    await user.click(screen.getByRole("button", { name: /로그 조회/ }));

    expect(await screen.findByText("API key is invalid.")).toBeInTheDocument();
  });

  it("입력한 조회 필터를 감사 로그 API에 전달한다", async () => {
    const user = userEvent.setup();
    const client = {
      listChatEvents: vi.fn().mockResolvedValue({ total: 0, events: [] }),
    };

    render(<AuditLogWorkspace client={client} />);

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.type(screen.getByLabelText("검색어"), "정책");
    await user.type(screen.getByLabelText("문서 ID"), "doc-1");
    await user.type(screen.getByLabelText("요청 ID"), "request-1");
    await user.type(screen.getByLabelText("시작 시각"), "2026-05-15T09:00");
    await user.type(screen.getByLabelText("종료 시각"), "2026-05-15T10:00");
    await user.clear(screen.getByLabelText("조회 개수"));
    await user.type(screen.getByLabelText("조회 개수"), "20");

    await user.click(screen.getByRole("button", { name: /로그 조회/ }));

    await waitFor(() => {
      expect(client.listChatEvents).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
        query: "정책",
        documentId: "doc-1",
        requestId: "request-1",
        occurredFrom: "2026-05-15T09:00",
        occurredTo: "2026-05-15T10:00",
        limit: 20,
      });
    });
  });
});
