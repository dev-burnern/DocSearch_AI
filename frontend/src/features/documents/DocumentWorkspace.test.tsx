import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DocumentWorkspace } from "./DocumentWorkspace";

describe("DocumentWorkspace", () => {
  it("문서를 업로드하고 인덱싱 결과를 표시한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn().mockResolvedValue({
        document_id: "doc-1",
        workspace_id: "workspace-alpha",
        workspace_name: "Workspace Alpha",
        filename: "memo.txt",
        parser: "text",
        character_count: 15,
        text_preview: "hello docsearch",
        storage_key: "workspace-alpha/doc-1/memo.txt",
        indexing_job_id: "job-1",
        indexing_status: "completed",
        chunk_count: 1,
      }),
      listDocuments: vi.fn(),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn(),
    };
    const searchClient = {
      searchDocuments: vi.fn(),
    };
    const file = new File(["hello docsearch"], "memo.txt", {
      type: "text/plain",
    });

    render(
      <DocumentWorkspace
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.upload(screen.getByLabelText("문서 파일"), file);

    const submit = screen.getByRole("button", { name: /문서 업로드/ });
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() => {
      expect(documentClient.uploadDocument).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
        file,
      });
    });
    expect(await screen.findByText("memo.txt")).toBeInTheDocument();
    expect(screen.getByText("doc-1")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("chunks 1")).toBeInTheDocument();
    expect(screen.getByText("hello docsearch")).toBeInTheDocument();
  });

  it("문서 검색 결과를 표시한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn(),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn(),
    };
    const searchClient = {
      searchDocuments: vi.fn().mockResolvedValue({
        query: "권한 정책",
        total: 1,
        results: [
          {
            document_id: "doc-1",
            filename: "policy.md",
            parser: "markdown",
            chunk_index: 2,
            score: 0.87,
            snippet: "권한 정책 문서 일부",
          },
        ],
      }),
    };

    render(
      <DocumentWorkspace
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.type(screen.getByLabelText("검색어"), "권한 정책");
    await user.type(screen.getByLabelText("검색 문서 ID"), "doc-1");

    const submit = screen.getByRole("button", { name: /문서 검색/ });
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() => {
      expect(searchClient.searchDocuments).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
        query: "권한 정책",
        documentIds: ["doc-1"],
        limit: 5,
      });
    });
    expect(await screen.findByText("policy.md")).toBeInTheDocument();
    expect(screen.getByText("권한 정책 문서 일부")).toBeInTheDocument();
    expect(screen.getByText("score 0.87")).toBeInTheDocument();
  });

  it("검색 결과가 비어 있으면 빈 상태를 보여준다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn(),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn(),
    };
    const searchClient = {
      searchDocuments: vi.fn().mockResolvedValue({
        query: "없는 문서",
        total: 0,
        results: [],
      }),
    };

    render(
      <DocumentWorkspace
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.type(screen.getByLabelText("검색어"), "없는 문서");
    await user.click(screen.getByRole("button", { name: /문서 검색/ }));

    expect(await screen.findByText("검색 결과가 없습니다.")).toBeInTheDocument();
  });

  it("업로드된 문서 목록을 조회하고 표시한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn().mockResolvedValue({
        total: 1,
        documents: [
          {
            document_id: "doc-1",
            workspace_id: "workspace-alpha",
            workspace_name: "Workspace Alpha",
            filename: "memo.txt",
            parser: "text",
            character_count: 15,
            text_preview: "hello docsearch",
            storage_key: "workspace-alpha/doc-1/memo.txt",
            indexing_job_id: "job-1",
            indexing_status: "completed",
            chunk_count: 1,
            uploaded_at: "2026-05-15T09:00:00Z",
          },
        ],
      }),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn(),
    };
    const searchClient = {
      searchDocuments: vi.fn(),
    };

    render(
      <DocumentWorkspace
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");

    const submit = screen.getByRole("button", { name: /문서 목록 조회/ });
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() => {
      expect(documentClient.listDocuments).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
      });
    });
    expect(await screen.findByText("memo.txt")).toBeInTheDocument();
    expect(screen.getByText("doc-1")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("chunks 1")).toBeInTheDocument();
    expect(screen.getByText("hello docsearch")).toBeInTheDocument();
  });

  it("문서 목록에서 문서를 삭제하고 목록에서 제거한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn().mockResolvedValue({
        total: 1,
        documents: [
          {
            document_id: "doc-1",
            workspace_id: "workspace-alpha",
            workspace_name: "Workspace Alpha",
            filename: "memo.txt",
            parser: "text",
            character_count: 15,
            text_preview: "hello docsearch",
            storage_key: "workspace-alpha/doc-1/memo.txt",
            indexing_job_id: "job-1",
            indexing_status: "completed",
            chunk_count: 1,
            uploaded_at: "2026-05-15T09:00:00Z",
          },
        ],
      }),
      deleteDocument: vi.fn().mockResolvedValue({
        document_id: "doc-1",
        workspace_id: "workspace-alpha",
        deleted: true,
      }),
      reindexDocument: vi.fn(),
    };
    const searchClient = {
      searchDocuments: vi.fn(),
    };

    render(
      <DocumentWorkspace
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.click(screen.getByRole("button", { name: /문서 목록 조회/ }));
    expect(await screen.findByText("memo.txt")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /삭제/ }));

    await waitFor(() => {
      expect(documentClient.deleteDocument).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
        documentId: "doc-1",
      });
    });
    expect(screen.queryByText("memo.txt")).not.toBeInTheDocument();
    expect(screen.getByText("업로드된 문서가 없습니다.")).toBeInTheDocument();
  });

  it("문서 목록에서 문서를 재인덱싱하고 갱신된 상태를 표시한다", async () => {
    const user = userEvent.setup();
    const documentClient = {
      uploadDocument: vi.fn(),
      listDocuments: vi.fn().mockResolvedValue({
        total: 1,
        documents: [
          {
            document_id: "doc-1",
            workspace_id: "workspace-alpha",
            workspace_name: "Workspace Alpha",
            filename: "memo.txt",
            parser: "text",
            character_count: 15,
            text_preview: "hello docsearch",
            storage_key: "workspace-alpha/doc-1/memo.txt",
            indexing_job_id: "job-1",
            indexing_status: "completed",
            chunk_count: 1,
            uploaded_at: "2026-05-15T09:00:00Z",
          },
        ],
      }),
      deleteDocument: vi.fn(),
      reindexDocument: vi.fn().mockResolvedValue({
        document_id: "doc-1",
        workspace_id: "workspace-alpha",
        workspace_name: "Workspace Alpha",
        filename: "memo.txt",
        parser: "text",
        character_count: 15,
        text_preview: "hello docsearch",
        storage_key: "workspace-alpha/doc-1/memo.txt",
        indexing_job_id: "job-2",
        indexing_status: "completed",
        chunk_count: 2,
        uploaded_at: "2026-05-15T09:00:00Z",
      }),
    };
    const searchClient = {
      searchDocuments: vi.fn(),
    };

    render(
      <DocumentWorkspace
        documentClient={documentClient}
        searchClient={searchClient}
      />,
    );

    await user.type(screen.getByLabelText("API Key"), "local-dev-key");
    await user.click(screen.getByRole("button", { name: /문서 목록 조회/ }));
    expect(await screen.findByText("chunks 1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /재인덱싱/ }));

    await waitFor(() => {
      expect(documentClient.reindexDocument).toHaveBeenCalledWith({
        apiKey: "local-dev-key",
        documentId: "doc-1",
      });
    });
    expect(await screen.findByText("chunks 2")).toBeInTheDocument();
  });
});
