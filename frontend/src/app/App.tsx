import { Alert, Button, Input, Layout, Space, Tabs, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import { ChatWorkspace } from "../features/chat/ChatWorkspace";
import { AuditLogWorkspace } from "../features/audit/AuditLogWorkspace";
import { DocumentWorkspace } from "../features/documents/DocumentWorkspace";
import {
  WorkspaceClient,
  WorkspaceContext,
  createWorkspaceApiClient,
} from "../lib/workspace-api";

const { Content, Header } = Layout;
const { Paragraph, Title } = Typography;

interface AppProps {
  workspaceClient?: WorkspaceClient;
}

export default function App({ workspaceClient }: AppProps) {
  const resolvedWorkspaceClient = useMemo(
    () => workspaceClient ?? createWorkspaceApiClient(),
    [workspaceClient],
  );
  const [apiKey, setApiKey] = useState("");
  const [confirmedApiKey, setConfirmedApiKey] = useState<string | null>(null);
  const [workspaceContext, setWorkspaceContext] =
    useState<WorkspaceContext | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [isCheckingWorkspace, setIsCheckingWorkspace] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");

  const canCheckWorkspace = apiKey.trim().length > 0 && !isCheckingWorkspace;
  const isAdmin = workspaceContext?.role === "admin";
  const sharedApiKey = confirmedApiKey ?? undefined;

  async function checkWorkspace() {
    if (!canCheckWorkspace) {
      return;
    }

    setIsCheckingWorkspace(true);
    setWorkspaceError(null);

    try {
      const nextContext = await resolvedWorkspaceClient.getWorkspace({
        apiKey: apiKey.trim(),
      });
      setWorkspaceContext(nextContext);
      setConfirmedApiKey(apiKey.trim());
      if (nextContext.role !== "admin" && activeTab === "audit") {
        setActiveTab("chat");
      }
    } catch (error) {
      setWorkspaceContext(null);
      setConfirmedApiKey(null);
      if (activeTab === "audit") {
        setActiveTab("chat");
      }
      setWorkspaceError(
        error instanceof Error ? error.message : "API Key 확인에 실패했습니다.",
      );
    } finally {
      setIsCheckingWorkspace(false);
    }
  }

  const tabItems = [
    {
      key: "chat",
      label: "채팅",
      children: <ChatWorkspace apiKey={sharedApiKey} />,
    },
    {
      key: "documents",
      label: "문서",
      children: <DocumentWorkspace apiKey={sharedApiKey} />,
    },
  ];

  if (isAdmin) {
    tabItems.push({
      key: "audit",
      label: "감사 로그",
      children: <AuditLogWorkspace apiKey={sharedApiKey} />,
    });
  }

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Space direction="vertical" size={2}>
          <Title level={3} className="app-title">
            DocSearch AI
          </Title>
          <Paragraph className="app-subtitle">
            온프레미스 RAG 문서 질의응답
          </Paragraph>
        </Space>
        <Space wrap size={8} className="app-tags">
          <Tag color="blue">React</Tag>
          <Tag color="green">FastAPI</Tag>
          <Tag color="purple">vLLM</Tag>
          <Tag color="cyan">Qdrant</Tag>
        </Space>
      </Header>
      <Content className="app-content">
        <section className="workspace-auth" aria-label="워크스페이스 인증">
          <form
            className="workspace-auth-form"
            onSubmit={(event) => {
              event.preventDefault();
              void checkWorkspace();
            }}
          >
            <label className="field-label" htmlFor="shared-api-key">
              공통 API Key
            </label>
            <Input.Password
              id="shared-api-key"
              autoComplete="off"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
            />
            <Button
              type="primary"
              htmlType="submit"
              loading={isCheckingWorkspace}
              disabled={!canCheckWorkspace}
            >
              키 확인
            </Button>
            {workspaceContext ? (
              <Space wrap>
                <Tag color="green">{workspaceContext.workspace_name}</Tag>
                <Tag color={workspaceContext.role === "admin" ? "purple" : "blue"}>
                  {workspaceContext.role}
                </Tag>
              </Space>
            ) : null}
          </form>
          {workspaceError ? (
            <Alert type="error" message={workspaceError} showIcon />
          ) : null}
        </section>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Content>
    </Layout>
  );
}
