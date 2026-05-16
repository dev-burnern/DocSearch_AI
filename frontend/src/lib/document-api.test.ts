import { describe, expect, it, vi } from "vitest";

import { createDocumentApiClient } from "./document-api";

describe("createDocumentApiClient", () => {
  it("문서 업로드 요청에 토큰, 파일, 보안 등급을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          document_id: "doc-1",
          workspace_id: "workspace-alpha",
          workspace_name: "Workspace Alpha",
          security_level: "confidential",
          filename: "memo.txt",
          parser: "text",
          character_count: 15,
          text_preview: "hello docsearch",
          storage_key: "workspace-alpha/doc-1/memo.txt",
          indexing_job_id: "job-1",
          indexing_status: "completed",
          chunk_count: 1,
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    const file = new File(["hello docsearch"], "memo.txt", {
      type: "text/plain",
    });
    const client = createDocumentApiClient({ baseUrl: "http://api.local", fetcher });

    const response = await client.uploadDocument({
      authToken: "auth-token",
      file,
      securityLevel: "confidential",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://api.local/v1/documents",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer auth-token" },
      }),
    );
    const body = fetcher.mock.calls[0][1].body as FormData;
    expect(body.get("file")).toBe(file);
    expect(body.get("security_level")).toBe("confidential");
    expect(response.document_id).toBe("doc-1");
  });

  it("문서 목록 조회에 토큰을 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ documents: [], total: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createDocumentApiClient({ baseUrl: "http://api.local/", fetcher });

    const response = await client.listDocuments({ authToken: "auth-token" });

    expect(fetcher).toHaveBeenCalledWith(
      "http://api.local/v1/documents",
      expect.objectContaining({
        method: "GET",
        headers: { Authorization: "Bearer auth-token" },
      }),
    );
    expect(response.total).toBe(0);
  });

  it("문서 삭제와 재인덱싱에 토큰과 문서 ID를 전송한다", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            workspace_id: "workspace-alpha",
            deleted: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
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
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    const client = createDocumentApiClient({ baseUrl: "http://api.local", fetcher });

    await client.deleteDocument({ authToken: "auth-token", documentId: "doc-1" });
    const record = await client.reindexDocument({
      authToken: "auth-token",
      documentId: "doc-1",
    });

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://api.local/v1/documents/doc-1",
      expect.objectContaining({
        method: "DELETE",
        headers: { Authorization: "Bearer auth-token" },
      }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://api.local/v1/documents/doc-1/reindex",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer auth-token" },
      }),
    );
    expect(record.chunk_count).toBe(2);
  });
});
