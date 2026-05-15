export type WorkspaceRole = "member" | "admin";

export interface WorkspaceRequest {
  apiKey: string;
}

export interface WorkspaceContext {
  request_id: string;
  workspace_id: string;
  workspace_name: string;
  role: WorkspaceRole;
}

export interface WorkspaceClient {
  getWorkspace(payload: WorkspaceRequest): Promise<WorkspaceContext>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface WorkspaceApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class WorkspaceApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkspaceApiError";
  }
}

export function createWorkspaceApiClient(
  options: WorkspaceApiClientOptions = {},
): WorkspaceClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async getWorkspace(payload: WorkspaceRequest): Promise<WorkspaceContext> {
      const response = await fetcher(`${baseUrl}/v1/workspace`, {
        method: "GET",
        headers: {
          "X-API-Key": payload.apiKey,
        },
      });

      if (!response.ok) {
        throw new WorkspaceApiError(await readErrorMessage(response));
      }

      return (await response.json()) as WorkspaceContext;
    },
  };
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `워크스페이스 API 요청에 실패했습니다. (${response.status})`;

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
