import { buildAuthHeaders } from "./auth-api";
import { DocumentSecurityLevel } from "./document-api";

export interface ChatSubmitPayload {
  authToken: string;
  question: string;
  documentIds: string[];
  securityLevels: DocumentSecurityLevel[];
  topK: number;
}

export interface ChatCitation {
  citation_id: number;
  document_id: string;
  filename: string;
  security_level: DocumentSecurityLevel;
  chunk_index: number;
  score: number;
  rerank_score?: number | null;
  snippet: string;
}

export interface ChatUsage {
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
}

export interface ChatResponse {
  answer: string;
  model: string;
  citations: ChatCitation[];
  usage: ChatUsage;
  retrieved_chunk_count: number;
}

export interface ChatClient {
  ask(payload: ChatSubmitPayload): Promise<ChatResponse>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface ChatApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class DocSearchApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DocSearchApiError";
  }
}

export function createChatApiClient(
  options: ChatApiClientOptions = {},
): ChatClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async ask(payload: ChatSubmitPayload): Promise<ChatResponse> {
      const response = await fetcher(`${baseUrl}/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...buildAuthHeaders(payload.authToken),
        },
        body: JSON.stringify(toChatRequestBody(payload)),
      });

      if (!response.ok) {
        throw new DocSearchApiError(await readErrorMessage(response));
      }

      return (await response.json()) as ChatResponse;
    },
  };
}

function toChatRequestBody(payload: ChatSubmitPayload) {
  return {
    question: payload.question,
    document_ids: payload.documentIds,
    security_levels: payload.securityLevels,
    top_k: payload.topK,
  };
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `채팅 API 요청에 실패했습니다. (${response.status})`;

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
