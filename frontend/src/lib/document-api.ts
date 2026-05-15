export interface DocumentUploadPayload {
  apiKey: string;
  file: File;
}

export interface DocumentListPayload {
  apiKey: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  workspace_id: string;
  workspace_name: string;
  filename: string;
  parser: string;
  character_count: number;
  text_preview: string;
  storage_key: string;
  indexing_job_id: string;
  indexing_status: string;
  chunk_count: number;
}

export interface DocumentRecord extends DocumentUploadResponse {
  uploaded_at: string;
}

export interface DocumentListResponse {
  documents: DocumentRecord[];
  total: number;
}

export interface DocumentClient {
  uploadDocument(payload: DocumentUploadPayload): Promise<DocumentUploadResponse>;
  listDocuments(payload: DocumentListPayload): Promise<DocumentListResponse>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface DocumentApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class DocumentApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DocumentApiError";
  }
}

export function createDocumentApiClient(
  options: DocumentApiClientOptions = {},
): DocumentClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async uploadDocument(
      payload: DocumentUploadPayload,
    ): Promise<DocumentUploadResponse> {
      const formData = new FormData();
      formData.append("file", payload.file);

      const response = await fetcher(`${baseUrl}/v1/documents`, {
        method: "POST",
        headers: {
          "X-API-Key": payload.apiKey,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new DocumentApiError(await readErrorMessage(response));
      }

      return (await response.json()) as DocumentUploadResponse;
    },

    async listDocuments(
      payload: DocumentListPayload,
    ): Promise<DocumentListResponse> {
      const response = await fetcher(`${baseUrl}/v1/documents`, {
        method: "GET",
        headers: {
          "X-API-Key": payload.apiKey,
        },
      });

      if (!response.ok) {
        throw new DocumentApiError(await readErrorMessage(response));
      }

      return (await response.json()) as DocumentListResponse;
    },
  };
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `문서 API 요청에 실패했습니다. (${response.status})`;

  try {
    const payload = (await response.json()) as {
      detail?: string | { message?: string };
    };

    if (typeof payload.detail === "string") {
      return payload.detail;
    }

    if (payload.detail?.message) {
      return payload.detail.message;
    }
  } catch {
    return fallback;
  }

  return fallback;
}
