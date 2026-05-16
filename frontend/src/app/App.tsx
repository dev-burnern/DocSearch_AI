import {
  AuditOutlined,
  FileOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MessageOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Alert, Button, Card, Input, Layout, Menu, Space, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import { AuditLogWorkspace } from "../features/audit/AuditLogWorkspace";
import { ChatWorkspace } from "../features/chat/ChatWorkspace";
import { DocumentWorkspace } from "../features/documents/DocumentWorkspace";
import { OperationsStatusWorkspace } from "../features/operations/OperationsStatusWorkspace";
import {
  AuthClient,
  AuthWorkspace,
  createAuthApiClient,
} from "../lib/auth-api";

const { Content, Header, Sider } = Layout;
const { Paragraph, Text, Title } = Typography;

interface AppProps {
  authClient?: AuthClient;
}

type ActiveView = "chat" | "documents" | "operations" | "audit";
type AuthMode = "login" | "signup";

export default function App({ authClient }: AppProps) {
  const resolvedAuthClient = useMemo(
    () => authClient ?? createAuthApiClient(),
    [authClient],
  );
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [workspaceContext, setWorkspaceContext] = useState<AuthWorkspace | null>(
    null,
  );
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [collapsed, setCollapsed] = useState(false);

  const isAuthenticated = authToken !== null && workspaceContext !== null;
  const isAdmin = workspaceContext?.role === "admin";
  const canSubmitAuth =
    employeeId.trim().length > 0 && password.length > 0 && !isAuthenticating;

  async function submitAuth() {
    if (!canSubmitAuth) {
      return;
    }

    setIsAuthenticating(true);
    setAuthError(null);

    try {
      const payload = {
        employeeId: employeeId.trim(),
        password,
        displayName: displayName.trim() || undefined,
      };
      const response =
        authMode === "login"
          ? await resolvedAuthClient.login(payload)
          : await resolvedAuthClient.signup(payload);
      setAuthToken(response.access_token);
      setWorkspaceContext(response.workspace);
      setActiveView("chat");
    } catch (error) {
      setAuthToken(null);
      setWorkspaceContext(null);
      setAuthError(
        error instanceof Error ? error.message : "로그인 요청에 실패했습니다.",
      );
    } finally {
      setIsAuthenticating(false);
    }
  }

  function logout() {
    setAuthToken(null);
    setWorkspaceContext(null);
    setPassword("");
    setActiveView("chat");
  }

  const menuItems = [
    {
      key: "chat",
      icon: <MessageOutlined />,
      label: "AI 채팅",
      disabled: !isAuthenticated,
    },
    {
      key: "documents",
      icon: <FileOutlined />,
      label: "문서 관리",
      disabled: !isAuthenticated,
    },
    {
      key: "operations",
      icon: <SettingOutlined />,
      label: "운영 상태",
      disabled: !isAdmin,
    },
    {
      key: "audit",
      icon: <AuditOutlined />,
      label: "감사 로그",
      disabled: !isAdmin,
    },
  ];

  return (
    <Layout className="app-shell">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        className="app-sider"
      >
        <div className="app-logo">
          <Text strong className="app-logo-text">
            {collapsed ? "DS" : "DocSearch AI"}
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={isAuthenticated ? [activeView] : []}
          items={menuItems}
          onClick={({ key }) => setActiveView(key as ActiveView)}
          className="app-menu"
        />
      </Sider>

      <Layout className="app-main-layout">
        <Header className="app-header">
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
          />

          {workspaceContext ? (
            <Space wrap size={8}>
              <Tag color="green">{workspaceContext.workspace_name}</Tag>
              <Tag color={workspaceContext.role === "admin" ? "purple" : "blue"}>
                {workspaceContext.role}
              </Tag>
              <Tag>{workspaceContext.employee_id}</Tag>
              <Button size="small" onClick={logout}>
                로그아웃
              </Button>
            </Space>
          ) : (
            <Text type="secondary">사번으로 로그인하세요</Text>
          )}
        </Header>

        <Content className="app-content">
          {!isAuthenticated ? (
            <AuthCard
              authMode={authMode}
              employeeId={employeeId}
              password={password}
              displayName={displayName}
              errorMessage={authError}
              isSubmitting={isAuthenticating}
              canSubmit={canSubmitAuth}
              onAuthModeChange={setAuthMode}
              onEmployeeIdChange={setEmployeeId}
              onPasswordChange={setPassword}
              onDisplayNameChange={setDisplayName}
              onSubmit={() => void submitAuth()}
            />
          ) : null}
          {isAuthenticated && activeView === "chat" ? (
            <ChatWorkspace authToken={authToken} />
          ) : null}
          {isAuthenticated && activeView === "documents" ? (
            <DocumentWorkspace authToken={authToken} />
          ) : null}
          {isAuthenticated && activeView === "operations" && isAdmin ? (
            <OperationsStatusWorkspace authToken={authToken} />
          ) : null}
          {isAuthenticated && activeView === "audit" && isAdmin ? (
            <AuditLogWorkspace authToken={authToken} />
          ) : null}
        </Content>
      </Layout>
    </Layout>
  );
}

interface AuthCardProps {
  authMode: AuthMode;
  employeeId: string;
  password: string;
  displayName: string;
  errorMessage: string | null;
  isSubmitting: boolean;
  canSubmit: boolean;
  onAuthModeChange(value: AuthMode): void;
  onEmployeeIdChange(value: string): void;
  onPasswordChange(value: string): void;
  onDisplayNameChange(value: string): void;
  onSubmit(): void;
}

function AuthCard({
  authMode,
  employeeId,
  password,
  displayName,
  errorMessage,
  isSubmitting,
  canSubmit,
  onAuthModeChange,
  onEmployeeIdChange,
  onPasswordChange,
  onDisplayNameChange,
  onSubmit,
}: AuthCardProps) {
  const isSignup = authMode === "signup";

  return (
    <Card className="auth-card" variant="borderless">
      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <Space direction="vertical" size={4}>
          <Title level={3} className="section-title">
            {isSignup ? "회원가입" : "로그인"}
          </Title>
          <Paragraph className="auth-copy">
            사번과 비밀번호로 DocSearch AI에 접속합니다.
          </Paragraph>
        </Space>

        <label className="field-label" htmlFor="employee-id">
          사번
        </label>
        <Input
          id="employee-id"
          autoComplete="username"
          value={employeeId}
          onChange={(event) => onEmployeeIdChange(event.target.value)}
        />

        {isSignup ? (
          <>
            <label className="field-label" htmlFor="display-name">
              이름
            </label>
            <Input
              id="display-name"
              autoComplete="name"
              value={displayName}
              onChange={(event) => onDisplayNameChange(event.target.value)}
            />
          </>
        ) : null}

        <label className="field-label" htmlFor="password">
          비밀번호
        </label>
        <Input.Password
          id="password"
          autoComplete={isSignup ? "new-password" : "current-password"}
          value={password}
          onChange={(event) => onPasswordChange(event.target.value)}
        />

        {errorMessage ? <Alert type="error" message={errorMessage} showIcon /> : null}

        <Button
          type="primary"
          htmlType="submit"
          loading={isSubmitting}
          disabled={!canSubmit}
        >
          {isSignup ? "회원가입" : "로그인"}
        </Button>
        <Button
          type="link"
          onClick={() => onAuthModeChange(isSignup ? "login" : "signup")}
        >
          {isSignup ? "이미 계정이 있나요? 로그인" : "계정이 없나요? 회원가입"}
        </Button>
      </form>
    </Card>
  );
}
