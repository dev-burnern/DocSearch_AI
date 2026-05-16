import { buildAuthHeaders } from "./auth-api";

export interface AuditLogRequest {
  authToken: string;
  query?: string;
  documentId?: string;
  requestId?: string;
  occurredFrom?: string;
  occurredTo?: string;
  limit?: number;
}

export interface AuditCitation {
  citation_id: number;
  document_id: string;
  filename: string;
  chunk_index: number;
  score: number;
  rerank_score?: number | null;
}

export interface ChatAuditEvent {
  event_id: string;
  event_type: string;
  occurred_at: string;
  request_id: string;
  workspace_id: string;
  workspace_name: string;
  question: string;
  document_ids?: string[] | null;
  retrieval_limit: number;
  rerank_top_k: number;
  retrieved_chunk_count: number;
  model: string;
  answer_preview: string;
  answer_character_count: number;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  citations: AuditCitation[];
}

export interface ChatAuditEventListResponse {
  events: ChatAuditEvent[];
  total: number;
}

export interface AuditLogExportResponse {
  filename: string;
  content: string;
  contentType: string;
}

export interface AuditLogClient {
  listChatEvents(payload: AuditLogRequest): Promise<ChatAuditEventListResponse>;
  exportChatEvents(payload: AuditLogRequest): Promise<AuditLogExportResponse>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface AuditLogApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class AuditLogApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuditLogApiError";
  }
}

export function createAuditLogApiClient(
  options: AuditLogApiClientOptions = {},
): AuditLogClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async listChatEvents(
      payload: AuditLogRequest,
    ): Promise<ChatAuditEventListResponse> {
      const response = await fetcher(
        `${baseUrl}/v1/audit-logs/chat${buildQueryString(payload)}`,
        {
          method: "GET",
          headers: buildAuthHeaders(payload.authToken),
        },
      );

      if (!response.ok) {
        throw new AuditLogApiError(await readErrorMessage(response));
      }

      return (await response.json()) as ChatAuditEventListResponse;
    },
    async exportChatEvents(
      payload: AuditLogRequest,
    ): Promise<AuditLogExportResponse> {
      const response = await fetcher(
        `${baseUrl}/v1/audit-logs/chat/export${buildQueryString(payload)}`,
        {
          method: "GET",
          headers: buildAuthHeaders(payload.authToken),
        },
      );

      if (!response.ok) {
        throw new AuditLogApiError(await readErrorMessage(response));
      }

      return {
        filename: readFilename(response.headers.get("Content-Disposition")),
        content: await response.text(),
        contentType:
          response.headers.get("Content-Type") ?? "text/csv; charset=utf-8",
      };
    },
  };
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

function buildQueryString(payload: AuditLogRequest): string {
  const params = new URLSearchParams();
  appendIfPresent(params, "query", payload.query);
  appendIfPresent(params, "document_id", payload.documentId);
  appendIfPresent(params, "request_id", payload.requestId);
  appendIfPresent(params, "from", payload.occurredFrom);
  appendIfPresent(params, "to", payload.occurredTo);

  if (payload.limit !== undefined) {
    params.set("limit", String(payload.limit));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

function appendIfPresent(
  params: URLSearchParams,
  key: string,
  value: string | undefined,
) {
  const trimmedValue = value?.trim();
  if (trimmedValue) {
    params.set(key, trimmedValue);
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `감사 로그 API 요청에 실패했습니다. (${response.status})`;

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

function readFilename(contentDisposition: string | null): string {
  if (!contentDisposition) {
    return "chat-audit-logs.csv";
  }

  const quotedFilename = /filename="([^"]+)"/.exec(contentDisposition);
  if (quotedFilename) {
    return quotedFilename[1];
  }

  const plainFilename = /filename=([^;]+)/.exec(contentDisposition);
  return plainFilename?.[1]?.trim() || "chat-audit-logs.csv";
}
