import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DocumentWorkspace } from "./DocumentWorkspace";

describe("DocumentWorkspace", () => {
  it("문서를 업로드하고 선택한 권한을 함께 전송한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn().mockResolvedValue(buildDocumentRecord()),
      listDocuments: vi.fn(),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn(),
    };
    const searchClient = { searchDocuments: vi.fn() };
    const file = new File(["hello docsearch"], "memo.txt", {
      type: "text/plain",
    });

    render(
      <DocumentWorkspace
        authToken="auth-token"
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.upload(screen.getByLabelText("문서 파일"), file);
    await user.click(screen.getByRole("button", { name: /문서 업로드/ }));

    await waitFor(() => {
      expect(documentClient.uploadDocument).toHaveBeenCalledWith({
        authToken: "auth-token",
        file,
        securityLevel: "internal",
      });
    });
    expect(await screen.findByText("memo.txt")).toBeInTheDocument();
    expect(screen.getAllByText("사내")).toHaveLength(2);
  });

  it("문서 검색 요청에 토큰과 검색 조건을 전송한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn(),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn(),
    };
    const searchClient = {
      searchDocuments: vi.fn().mockResolvedValue({
        query: "권한",
        total: 1,
        results: [
          {
            document_id: "doc-1",
            filename: "policy.md",
            parser: "markdown",
            security_level: "internal",
            chunk_index: 2,
            score: 0.87,
            snippet: "권한 정책 문서 일부",
          },
        ],
      }),
    };

    render(
      <DocumentWorkspace
        authToken="auth-token"
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("검색어"), "권한");
    await user.type(screen.getByLabelText("검색 문서 ID"), "doc-1");
    await user.click(screen.getByRole("button", { name: /문서 검색/ }));

    await waitFor(() => {
      expect(searchClient.searchDocuments).toHaveBeenCalledWith({
        authToken: "auth-token",
        query: "권한",
        documentIds: ["doc-1"],
        securityLevels: [],
        limit: 5,
      });
    });
    expect(await screen.findByText("policy.md")).toBeInTheDocument();
  });

  it("문서 목록 조회와 삭제 요청을 처리한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn().mockResolvedValue({
        total: 1,
        documents: [buildDocumentRecord()],
      }),
      deleteDocument: vi.fn().mockResolvedValue({
        document_id: "doc-1",
        workspace_id: "workspace-alpha",
        deleted: true,
      }),
      reindexDocument: vi.fn(),
    };
    const searchClient = { searchDocuments: vi.fn() };

    render(
      <DocumentWorkspace
        authToken="auth-token"
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.click(screen.getByRole("button", { name: /문서 목록 조회/ }));
    expect(await screen.findByText("memo.txt")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /삭제/ }));

    await waitFor(() => {
      expect(documentClient.deleteDocument).toHaveBeenCalledWith({
        authToken: "auth-token",
        documentId: "doc-1",
      });
    });
  });
});

function buildDocumentRecord() {
  return {
    document_id: "doc-1",
    workspace_id: "workspace-alpha",
    workspace_name: "Workspace Alpha",
    uploaded_by_employee_id: "1002",
    security_level: "internal" as const,
    filename: "memo.txt",
    parser: "text",
    character_count: 15,
    text_preview: "hello docsearch",
    storage_key: "workspace-alpha/doc-1/memo.txt",
    indexing_job_id: "job-1",
    indexing_status: "completed",
    chunk_count: 1,
    uploaded_at: "2026-05-15T09:00:00Z",
  };
}
