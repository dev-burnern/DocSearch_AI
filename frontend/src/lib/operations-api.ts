export type OperationsStatus = "ready" | "not_ready";

export interface OperationsStatusRequest {
  apiKey: string;
}

export interface OperationsWorkspaceSummary {
  workspace_id: string;
  workspace_name: string;
  role: "member" | "admin";
}

export interface OperationsCheck {
  name: string;
  status: OperationsStatus;
  message: string;
}

export interface OperationEvent {
  event_id: string;
  event_type: string;
  severity: "info" | "warning" | "error";
  source: string;
  message: string;
  occurred_at: string;
  details: Record<string, string>;
}

export interface OperationsSettingsSummary {
  environment: string;
  debug: boolean;
  dependency_health_checks_enabled: boolean;
  dependency_health_timeout_seconds: number;
  retrieval_mode: string;
  hybrid_dense_weight: number;
  hybrid_lexical_weight: number;
  hybrid_candidate_limit: number;
  rate_limit: {
    enabled: boolean;
    backend: string;
    requests: number;
    window_seconds: number;
    fail_open: boolean;
  };
  backends: {
    audit_log: string;
    document_metadata: string;
    indexing_queue: string;
    embedding: string;
    reranker: string;
  };
  models: {
    llm: string;
    llm_timeout_seconds: number;
    llm_max_tokens: number;
    llm_temperature: number;
    llm_max_retries: number;
    llm_retry_backoff_seconds: number;
    embedding: string;
    reranker: string;
    embedding_vector_size: number;
  };
}

export interface IndexingQueueSummary {
  backend: string;
  status: OperationsStatus;
  queue_key: string | null;
  pending_jobs: number | null;
  max_attempts: number;
  message: string;
}

export interface OperationsStatusResponse {
  status: OperationsStatus;
  service: string;
  workspace: OperationsWorkspaceSummary;
  checks: OperationsCheck[];
  events: OperationEvent[];
  settings: OperationsSettingsSummary;
  indexing_queue: IndexingQueueSummary;
}

export interface OperationsClient {
  getOperationsStatus(
    payload: OperationsStatusRequest,
  ): Promise<OperationsStatusResponse>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface OperationsApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class OperationsApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "OperationsApiError";
  }
}

export function createOperationsApiClient(
  options: OperationsApiClientOptions = {},
): OperationsClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async getOperationsStatus(
      payload: OperationsStatusRequest,
    ): Promise<OperationsStatusResponse> {
      const response = await fetcher(`${baseUrl}/v1/admin/operations`, {
        method: "GET",
        headers: {
          "X-API-Key": payload.apiKey,
        },
      });

      if (!response.ok) {
        throw new OperationsApiError(await readErrorMessage(response));
      }

      return (await response.json()) as OperationsStatusResponse;
    },
  };
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `운영 상태 API 요청에 실패했습니다. (${response.status})`;

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
