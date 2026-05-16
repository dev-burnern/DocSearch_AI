export type WorkspaceRole = "member" | "admin";

export interface AuthRequest {
  employeeId: string;
  password: string;
  displayName?: string;
}

export interface AuthWorkspace {
  request_id: string;
  workspace_id: string;
  workspace_name: string;
  role: WorkspaceRole;
  employee_id: string;
  display_name?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  workspace: AuthWorkspace;
}

export interface AuthClient {
  login(payload: AuthRequest): Promise<AuthResponse>;
  signup(payload: AuthRequest): Promise<AuthResponse>;
}

type Fetcher = (input: string, init: RequestInit) => Promise<Response>;

interface AuthApiClientOptions {
  baseUrl?: string;
  fetcher?: Fetcher;
}

export class AuthApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthApiError";
  }
}

export function createAuthApiClient(
  options: AuthApiClientOptions = {},
): AuthClient {
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api",
  );
  const fetcher =
    options.fetcher ??
    ((input: string, init: RequestInit) => globalThis.fetch(input, init));

  return {
    async login(payload: AuthRequest): Promise<AuthResponse> {
      return submitAuthRequest(fetcher, `${baseUrl}/v1/auth/login`, payload);
    },
    async signup(payload: AuthRequest): Promise<AuthResponse> {
      return submitAuthRequest(fetcher, `${baseUrl}/v1/auth/signup`, payload);
    },
  };
}

export function buildAuthHeaders(authToken: string): Record<string, string> {
  return {
    Authorization: `Bearer ${authToken}`,
  };
}

async function submitAuthRequest(
  fetcher: Fetcher,
  url: string,
  payload: AuthRequest,
): Promise<AuthResponse> {
  const response = await fetcher(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      employee_id: payload.employeeId,
      password: payload.password,
      display_name: payload.displayName,
    }),
  });

  if (!response.ok) {
    throw new AuthApiError(await readErrorMessage(response));
  }

  return (await response.json()) as AuthResponse;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `인증 요청에 실패했습니다. (${response.status})`;

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
