import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AuthClient, AuthResponse } from "../lib/auth-api";
import App from "./App";

describe("App", () => {
  it("로그인 전에는 사번 로그인 화면을 보여준다", () => {
    render(<App />);

    expect(screen.getByText("DocSearch AI")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "로그인" })).toBeInTheDocument();
    expect(screen.getByLabelText("사번")).toBeInTheDocument();
    expect(screen.getByLabelText("비밀번호")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /AI 채팅/ })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.queryByLabelText("API Key")).not.toBeInTheDocument();
  });

  it("관리자로 로그인하면 운영 상태와 감사 로그 메뉴를 사용할 수 있다", async () => {
    const user = userEvent.setup();
    const authClient = createAuthClient(
      buildAuthResponse({ role: "admin", employee_id: "1001" }),
    );

    render(<App authClient={authClient} />);

    await user.type(screen.getByLabelText("사번"), "1001");
    await user.type(screen.getByLabelText("비밀번호"), "password");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(await screen.findByText("Local Workspace")).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("1001")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /운영 상태/ })).not.toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("menuitem", { name: /감사 로그/ })).not.toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(authClient.loginRequests).toEqual([
      { employeeId: "1001", password: "password", displayName: undefined },
    ]);
  });

  it("일반 사용자로 로그인하면 관리자 메뉴는 비활성화한다", async () => {
    const user = userEvent.setup();
    const authClient = createAuthClient(
      buildAuthResponse({ role: "member", employee_id: "1002" }),
    );

    render(<App authClient={authClient} />);

    await user.type(screen.getByLabelText("사번"), "1002");
    await user.type(screen.getByLabelText("비밀번호"), "password");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(await screen.findByText("member")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /운영 상태/ })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("menuitem", { name: /감사 로그/ })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("회원가입 화면에서 이름과 사번, 비밀번호를 전송한다", async () => {
    const user = userEvent.setup();
    const authClient = createAuthClient(
      buildAuthResponse({ role: "member", employee_id: "2001" }),
    );

    render(<App authClient={authClient} />);

    await user.click(screen.getByRole("button", { name: /회원가입/ }));
    await user.type(screen.getByLabelText("사번"), "2001");
    await user.type(screen.getByLabelText("이름"), "홍길동");
    await user.type(screen.getByLabelText("비밀번호"), "pass1234");
    await user.click(screen.getByRole("button", { name: "회원가입" }));

    expect(await screen.findByText("2001")).toBeInTheDocument();
    expect(authClient.signupRequests).toEqual([
      { employeeId: "2001", password: "pass1234", displayName: "홍길동" },
    ]);
  });

  it("로그인 실패 메시지를 보여준다", async () => {
    const user = userEvent.setup();
    const authClient: AuthClient = {
      async login() {
        throw new Error("사번 또는 비밀번호가 올바르지 않습니다.");
      },
      async signup() {
        throw new Error("not used");
      },
    };

    render(<App authClient={authClient} />);

    await user.type(screen.getByLabelText("사번"), "9999");
    await user.type(screen.getByLabelText("비밀번호"), "wrong");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(
      await screen.findByText("사번 또는 비밀번호가 올바르지 않습니다."),
    ).toBeInTheDocument();
  });
});

function createAuthClient(response: AuthResponse): AuthClient & {
  loginRequests: unknown[];
  signupRequests: unknown[];
} {
  const loginRequests: unknown[] = [];
  const signupRequests: unknown[] = [];
  return {
    loginRequests,
    signupRequests,
    async login(payload) {
      loginRequests.push(payload);
      return response;
    },
    async signup(payload) {
      signupRequests.push(payload);
      return response;
    },
  };
}

function buildAuthResponse(
  overrides: Partial<AuthResponse["workspace"]> = {},
): AuthResponse {
  return {
    access_token: "auth-token",
    token_type: "bearer",
    workspace: {
      request_id: "req_1",
      workspace_id: "local-workspace",
      workspace_name: "Local Workspace",
      role: "member",
      employee_id: "1002",
      display_name: "사용자",
      ...overrides,
    },
  };
}
