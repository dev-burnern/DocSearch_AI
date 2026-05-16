import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AuditLogWorkspace } from "./AuditLogWorkspace";

describe("AuditLogWorkspace", () => {
  it("채팅 감사 로그를 조회하고 이벤트를 표시한다", async () => {
    const user = userEvent.setup();
    const client = {
      exportChatEvents: vi.fn(),
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
            model: "local-model",
            answer_preview: "문서 기반 답변입니다.",
            answer_character_count: 12,
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

    render(<AuditLogWorkspace authToken="auth-token" client={client} />);

    await user.click(screen.getByRole("button", { name: /로그 조회/ }));

    await waitFor(() => {
      expect(client.listChatEvents).toHaveBeenCalledWith({
        authToken: "auth-token",
      });
    });
    expect(await screen.findByText("정책 문서 요약해줘")).toBeInTheDocument();
    expect(screen.getByText("policy.md")).toBeInTheDocument();
    expect(screen.getByText("tokens 16")).toBeInTheDocument();
  });

  it("필터와 CSV 내보내기 요청을 전송한다", async () => {
    const user = userEvent.setup();
    const downloadFile = vi.fn();
    const client = {
      listChatEvents: vi.fn().mockResolvedValue({ total: 0, events: [] }),
      exportChatEvents: vi.fn().mockResolvedValue({
        filename: "chat-audit-logs.csv",
        content: "event_id\n1\n",
        contentType: "text/csv; charset=utf-8",
      }),
    };

    render(
      <AuditLogWorkspace
        authToken="auth-token"
        client={client}
        downloadFile={downloadFile}
      />,
    );

    await user.type(screen.getByLabelText("검색어"), "정책");
    await user.type(screen.getByLabelText("문서 ID"), "doc-1");
    await user.clear(screen.getByLabelText("조회 개수"));
    await user.type(screen.getByLabelText("조회 개수"), "20");
    await user.click(screen.getByRole("button", { name: /CSV 내보내기/ }));

    await waitFor(() => {
      expect(client.exportChatEvents).toHaveBeenCalledWith({
        authToken: "auth-token",
        query: "정책",
        documentId: "doc-1",
        limit: 20,
      });
    });
    expect(downloadFile).toHaveBeenCalled();
  });

  it("조회 실패 메시지를 보여준다", async () => {
    const user = userEvent.setup();
    const client = {
      exportChatEvents: vi.fn(),
      listChatEvents: vi.fn().mockRejectedValue(new Error("로그 조회 실패")),
    };

    render(<AuditLogWorkspace authToken="auth-token" client={client} />);

    await user.click(screen.getByRole("button", { name: /로그 조회/ }));

    expect(await screen.findByText("로그 조회 실패")).toBeInTheDocument();
  });
});
