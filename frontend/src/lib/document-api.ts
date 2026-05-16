import { buildAuthHeaders } from "./auth-api";

export interface DocumentUploadPayload {
  authToken: string;
  file: File;
  securityLevel: DocumentSecurityLevel;
}

export interface DocumentListPayload {
  authToken: string;
}

export interface DocumentActionPayload {
  authToken: string;
  documentId: string;
}

export type DocumentSecurityLevel =
  | "general"
  | "internal"
  | "confidential"
  | "restricted";

export interface DocumentUploadResponse {
  document_id: string;
  workspace_id: string;
  workspace_name: string;
  uploaded_by_employee_id?: string | null;
  security_level?: DocumentSecurityLevel;
  filename: string;
  parser: string;
  character_count: number;
  text_preview: string;
  storage_key: string;
  indexing_job_id: string;
  indexing_status: string;
  indexing_error?: string | null;
  chunk_count: number;
}

export interface DocumentRecord extends DocumentUploadResponse {
  uploaded_at: string;
}

export interface DocumentListResponse {
  documents: DocumentRecord[];
  total: number;
}

export interface DocumentDeleteResponse {
  document_id: string;
  workspace_id: string;
  deleted: boolean;
}

export interface DocumentClient {
  uploadDocument(payload: DocumentUploadPayload): Promise<DocumentUploadResponse>;
  listDocuments(payload: DocumentListPayload): Promise<DocumentListResponse>;
  deleteDocument(payload: DocumentActionPayload): Promise<DocumentDeleteResponse>;
  reindexDocument(payload: DocumentActionPayload): Promise<DocumentRecord>;
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
      formData.append("security_level", payload.securityLevel);

      const response = await fetcher(`${baseUrl}/v1/documents`, {
        method: "POST",
        headers: buildAuthHeaders(payload.authToken),
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
        headers: buildAuthHeaders(payload.authToken),
      });

      if (!response.ok) {
        throw new DocumentApiError(await readErrorMessage(response));
      }

      return (await response.json()) as DocumentListResponse;
    },

    async deleteDocument(
      payload: DocumentActionPayload,
    ): Promise<DocumentDeleteResponse> {
      const response = await fetcher(
        `${baseUrl}/v1/documents/${encodeURIComponent(payload.documentId)}`,
        {
          method: "DELETE",
          headers: buildAuthHeaders(payload.authToken),
        },
      );

      if (!response.ok) {
        throw new DocumentApiError(await readErrorMessage(response));
      }

      return (await response.json()) as DocumentDeleteResponse;
    },

    async reindexDocument(payload: DocumentActionPayload): Promise<DocumentRecord> {
      const response = await fetcher(
        `${baseUrl}/v1/documents/${encodeURIComponent(payload.documentId)}/reindex`,
        {
          method: "POST",
          headers: buildAuthHeaders(payload.authToken),
        },
      );

      if (!response.ok) {
        throw new DocumentApiError(await readErrorMessage(response));
      }

      return (await response.json()) as DocumentRecord;
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
