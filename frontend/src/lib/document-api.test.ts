import { describe, expect, it, vi } from "vitest";

import { createDocumentApiClient } from "./document-api";

describe("createDocumentApiClient", () => {
  it("문서 업로드 API에 API Key와 파일 FormData를 전송한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
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
    const client = createDocumentApiClient({
      baseUrl: "http://api.local",
      fetcher,
    });

    const response = await client.uploadDocument({
      apiKey: "local-dev-key",
      file,
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://api.local/v1/documents",
      expect.objectContaining({
        method: "POST",
        headers: {
          "X-API-Key": "local-dev-key",
        },
      }),
    );
    const body = fetcher.mock.calls[0][1].body as FormData;
    expect(body.get("file")).toBe(file);
    expect(response.document_id).toBe("doc-1");
  });

  it("업로드 API 오류 메시지를 사용자에게 전달할 수 있는 오류로 변환한다", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "DOCUMENT_UNSUPPORTED_TYPE",
            message: "Unsupported document type: .csv",
          },
        }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = createDocumentApiClient({
      baseUrl: "",
      fetcher,
    });

    await expect(
      client.uploadDocument({
        apiKey: "local-dev-key",
        file: new File(["a,b"], "table.csv", { type: "text/csv" }),
      }),
    ).rejects.toThrow("Unsupported document type: .csv");
  });
});
