import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "./App";
import { WorkspaceClient, WorkspaceContext } from "../lib/workspace-api";

describe("App", () => {
  it("채팅 작업 화면을 기본 화면으로 보여준다", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "DocSearch AI" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("API Key")).toBeInTheDocument();
    expect(screen.getByLabelText("질문")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /질문 보내기/ }),
    ).toBeDisabled();
    expect(screen.queryByRole("tab", { name: "감사 로그" })).not.toBeInTheDocument();
  });

  it("관리자 API Key를 확인하면 감사 로그 탭을 보여준다", async () => {
    const user = userEvent.setup();
    const workspaceClient = createWorkspaceClient({
      request_id: "req_1",
      workspace_id: "workspace-alpha",
      workspace_name: "Workspace Alpha",
      role: "admin",
    });

    render(<App workspaceClient={workspaceClient} />);

    await user.type(screen.getByLabelText("공통 API Key"), "admin-key");
    await user.click(screen.getByRole("button", { name: /키 확인/ }));

    expect(await screen.findByText("Workspace Alpha")).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "운영 상태" }));

    expect(
      screen.getByRole("heading", { name: "운영 상태" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "감사 로그" }));

    expect(
      screen.getByRole("heading", { name: "채팅 감사 로그" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /로그 조회/ }),
    ).toBeEnabled();
    expect(workspaceClient.requests).toEqual(["admin-key"]);
  });

  it("일반 사용자 API Key를 확인하면 감사 로그 탭을 숨긴다", async () => {
    const user = userEvent.setup();
    const workspaceClient = createWorkspaceClient({
      request_id: "req_1",
      workspace_id: "workspace-alpha",
      workspace_name: "Workspace Alpha",
      role: "member",
    });

    render(<App workspaceClient={workspaceClient} />);

    await user.type(screen.getByLabelText("공통 API Key"), "member-key");
    await user.click(screen.getByRole("button", { name: /키 확인/ }));

    expect(await screen.findByText("Workspace Alpha")).toBeInTheDocument();
    expect(screen.getByText("member")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "운영 상태" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "감사 로그" })).not.toBeInTheDocument();
  });

  it("감사 로그 탭에서 일반 사용자로 재확인하면 채팅 탭으로 이동한다", async () => {
    const user = userEvent.setup();
    const workspaceClient = createSequenceWorkspaceClient([
      {
        request_id: "req_1",
        workspace_id: "workspace-alpha",
        workspace_name: "Workspace Alpha",
        role: "admin",
      },
      {
        request_id: "req_2",
        workspace_id: "workspace-alpha",
        workspace_name: "Workspace Alpha",
        role: "member",
      },
    ]);

    render(<App workspaceClient={workspaceClient} />);

    const apiKeyInput = screen.getByLabelText("공통 API Key");
    await user.type(apiKeyInput, "admin-key");
    await user.click(screen.getByRole("button", { name: /키 확인/ }));
    await user.click(await screen.findByRole("tab", { name: "운영 상태" }));
    expect(
      screen.getByRole("heading", { name: "운영 상태" }),
    ).toBeInTheDocument();

    await user.clear(apiKeyInput);
    await user.type(apiKeyInput, "member-key");
    await user.click(screen.getByRole("button", { name: /키 확인/ }));

    expect(screen.queryByRole("tab", { name: "운영 상태" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "감사 로그" })).not.toBeInTheDocument();
    expect(screen.getByRole("tabpanel", { name: "채팅" })).toBeInTheDocument();
  });

  it("API Key 확인 실패 메시지를 보여준다", async () => {
    const user = userEvent.setup();
    const workspaceClient: WorkspaceClient = {
      async getWorkspace() {
        throw new Error("API key is invalid.");
      },
    };

    render(<App workspaceClient={workspaceClient} />);

    await user.type(screen.getByLabelText("공통 API Key"), "bad-key");
    await user.click(screen.getByRole("button", { name: /키 확인/ }));

    expect(await screen.findByText("API key is invalid.")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "감사 로그" })).not.toBeInTheDocument();
  });

  it("문서 탭으로 전환한다", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(screen.getByRole("tab", { name: "문서" }));

    expect(
      screen.getByRole("heading", { name: "문서 업로드" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /문서 업로드/ }),
    ).toBeDisabled();
  });
});

function createWorkspaceClient(context: WorkspaceContext): WorkspaceClient & {
  requests: string[];
} {
  const requests: string[] = [];
  return {
    requests,
    async getWorkspace(payload) {
      requests.push(payload.apiKey);
      return context;
    },
  };
}

function createSequenceWorkspaceClient(
  contexts: WorkspaceContext[],
): WorkspaceClient {
  let index = 0;
  return {
    async getWorkspace() {
      const context = contexts[index] ?? contexts[contexts.length - 1];
      index += 1;
      return context;
    },
  };
}
