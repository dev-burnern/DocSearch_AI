import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Input, List, Space, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import {
  OperationsCheck,
  OperationsClient,
  OperationsStatusResponse,
  createOperationsApiClient,
} from "../../lib/operations-api";

const { Paragraph, Text, Title } = Typography;

interface OperationsStatusWorkspaceProps {
  client?: OperationsClient;
  apiKey?: string;
}

export function OperationsStatusWorkspace({
  client,
  apiKey: confirmedApiKey,
}: OperationsStatusWorkspaceProps) {
  const operationsClient = useMemo(
    () => client ?? createOperationsApiClient(),
    [client],
  );
  const [apiKey, setApiKey] = useState("");
  const [response, setResponse] = useState<OperationsStatusResponse | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const resolvedApiKey = confirmedApiKey ?? apiKey.trim();
  const canSubmit = resolvedApiKey.length > 0 && !isLoading;

  async function loadOperationsStatus() {
    if (!canSubmit) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const nextResponse = await operationsClient.getOperationsStatus({
        apiKey: resolvedApiKey,
      });
      setResponse(nextResponse);
    } catch (error) {
      setResponse(null);
      setErrorMessage(
        error instanceof Error ? error.message : "운영 상태 조회에 실패했습니다.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="operations-workspace" aria-label="운영 상태 화면">
      <Card className="chat-panel" title="조회" variant="borderless">
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void loadOperationsStatus();
          }}
        >
          {confirmedApiKey ? null : (
            <>
              <label className="field-label" htmlFor="operations-api-key">
                API Key
              </label>
              <Input.Password
                id="operations-api-key"
                autoComplete="off"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </>
          )}

          <Button
            type="primary"
            htmlType="submit"
            icon={<ReloadOutlined />}
            loading={isLoading}
            disabled={!canSubmit}
          >
            상태 새로고침
          </Button>
        </form>
      </Card>

      <Card className="chat-panel operations-main" variant="borderless">
        <Space direction="vertical" size={16} className="chat-main-stack">
          <Space className="audit-heading" align="start">
            <div>
              <Title level={4} className="section-title">
                운영 상태
              </Title>
              <Paragraph className="audit-subtitle">
                readiness, 의존성 점검, 런타임 설정을 확인합니다.
              </Paragraph>
            </div>
            {response ? (
              <Tag color={response.status === "ready" ? "green" : "red"}>
                {response.status}
              </Tag>
            ) : null}
          </Space>

          {errorMessage ? (
            <Alert type="error" message={errorMessage} showIcon />
          ) : null}

          {!response && !errorMessage ? (
            <Empty description="운영 상태를 조회하세요." />
          ) : null}

          {response ? <OperationsSummary response={response} /> : null}
        </Space>
      </Card>
    </section>
  );
}

function OperationsSummary({ response }: { response: OperationsStatusResponse }) {
  return (
    <Space direction="vertical" size={16} className="chat-main-stack">
      <Space wrap>
        <Tag color="green">{response.workspace.workspace_name}</Tag>
        <Tag color="purple">{response.workspace.role}</Tag>
        <Tag>{response.settings.environment}</Tag>
        <Tag color={response.settings.debug ? "red" : "blue"}>
          debug {response.settings.debug ? "on" : "off"}
        </Tag>
        <Tag color={response.settings.rate_limit.enabled ? "green" : "default"}>
          rate limit {response.settings.rate_limit.requests}/
          {response.settings.rate_limit.window_seconds}s
        </Tag>
      </Space>

      <Card size="small" title="런타임 설정" variant="borderless">
        <Space wrap>
          <Tag>audit {response.settings.backends.audit_log}</Tag>
          <Tag>metadata {response.settings.backends.document_metadata}</Tag>
          <Tag>queue {response.settings.backends.indexing_queue}</Tag>
          <Tag>reranker {response.settings.backends.reranker}</Tag>
          <Tag>{response.settings.models.llm}</Tag>
          <Tag>{response.settings.models.reranker}</Tag>
          <Tag>vector {response.settings.models.embedding_vector_size}</Tag>
        </Space>
      </Card>

      <List
        className="operations-check-list"
        dataSource={response.checks}
        renderItem={(check) => <OperationsCheckItem check={check} />}
      />
    </Space>
  );
}

function OperationsCheckItem({ check }: { check: OperationsCheck }) {
  return (
    <List.Item className="audit-event-item">
      <Space direction="vertical" size={6} className="chat-main-stack">
        <Space wrap>
          <Text strong>{check.name}</Text>
          <Tag color={check.status === "ready" ? "green" : "red"}>
            {check.status}
          </Tag>
        </Space>
        <Paragraph className="answer-text">{check.message}</Paragraph>
      </Space>
    </List.Item>
  );
}
