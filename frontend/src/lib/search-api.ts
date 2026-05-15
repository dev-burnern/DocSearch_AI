export interface SearchSubmitPayload {
  apiKey: string;
  query: string;
  documentIds: string[];
  limit: number;
}

export interface SearchResultChunk {
  document_id: string;
  filename: string;
  parser: string;
  chunk_index: number;
  score: number;
  snippet: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResultChunk[];
}

export interface SearchClient {
  searchDocuments(payload: SearchSubmitPayload): Promise<SearchResponse>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface SearchApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class SearchApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SearchApiError";
  }
}

export function createSearchApiClient(
  options: SearchApiClientOptions = {},
): SearchClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async searchDocuments(
      payload: SearchSubmitPayload,
    ): Promise<SearchResponse> {
      const response = await fetcher(`${baseUrl}/v1/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": payload.apiKey,
        },
        body: JSON.stringify({
          query: payload.query,
          document_ids: payload.documentIds,
          limit: payload.limit,
        }),
      });

      if (!response.ok) {
        throw new SearchApiError(await readErrorMessage(response));
      }

      return (await response.json()) as SearchResponse;
    },
  };
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `검색 API 요청에 실패했습니다. (${response.status})`;

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
