import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatWorkspace } from "./ChatWorkspace";

describe("ChatWorkspace", () => {
  it("질문을 전송하고 답변과 출처를 표시한다", async () => {
    const user = userEvent.setup();
    const client = {
      ask: vi.fn().mockResolvedValue({
        answer: "권한이 허용된 문서 기준으로 답변합니다. [1]",
        model: "google/gemma-4-E4B-it",
        citations: [
          {
            citation_id: 1,
            document_id: "doc-1",
            filename: "policy.md",
            security_level: "internal",
            chunk_index: 0,
            score: 0.88,
            rerank_score: 0.94,
            snippet: "문서 일부",
          },
        ],
        usage: {
          prompt_tokens: 10,
          completion_tokens: 6,
          total_tokens: 16,
        },
        retrieved_chunk_count: 1,
      }),
    };

    render(<ChatWorkspace authToken="auth-token" client={client} />);

    await user.type(screen.getByLabelText("문서 ID"), "doc-1, doc-2");
    await user.type(screen.getByLabelText("질문"), "정책 문서 요약해줘");

    const submit = screen.getByRole("button", { name: /질문 보내기/ });
    expect(submit).toBeEnabled();

    await user.click(submit);

    await waitFor(() => {
      expect(client.ask).toHaveBeenCalledWith({
        authToken: "auth-token",
        question: "정책 문서 요약해줘",
        documentIds: ["doc-1", "doc-2"],
        securityLevels: [],
        topK: 5,
      });
    });

    expect(
      await screen.findByText("권한이 허용된 문서 기준으로 답변합니다. [1]"),
    ).toBeInTheDocument();
    expect(screen.getByText("google/gemma-4-E4B-it")).toBeInTheDocument();
    expect(screen.getByText("policy.md")).toBeInTheDocument();
    expect(screen.getByText("문서 일부")).toBeInTheDocument();
  });
});
