import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, List, Space, Tag, Typography } from "antd";
import { useMemo, useState } from "react";

import {
  OperationEvent,
  OperationsCheck,
  OperationsClient,
  OperationsStatusResponse,
  createOperationsApiClient,
} from "../../lib/operations-api";

const { Paragraph, Text, Title } = Typography;

interface OperationsStatusWorkspaceProps {
  client?: OperationsClient;
  authToken: string;
}

export function OperationsStatusWorkspace({
  client,
  authToken,
}: OperationsStatusWorkspaceProps) {
  const operationsClient = useMemo(
    () => client ?? createOperationsApiClient(),
    [client],
  );
  const [response, setResponse] = useState<OperationsStatusResponse | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const canSubmit = authToken.length > 0 && !isLoading;

  async function loadOperationsStatus() {
    if (!canSubmit) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const nextResponse = await operationsClient.getOperationsStatus({
        authToken,
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
        <Tag>rate backend {response.settings.rate_limit.backend}</Tag>
        <Tag color={response.settings.rate_limit.fail_open ? "blue" : "orange"}>
          fail-open {response.settings.rate_limit.fail_open ? "on" : "off"}
        </Tag>
        <Tag>retrieval {response.settings.retrieval_mode}</Tag>
        <Tag>
          hybrid {response.settings.hybrid_dense_weight}/
          {response.settings.hybrid_lexical_weight}
        </Tag>
        <Tag color={response.indexing_queue.status === "ready" ? "green" : "red"}>
          indexing queue {response.indexing_queue.status}
        </Tag>
        <Tag>
          pending {response.indexing_queue.pending_jobs ?? "unknown"}
        </Tag>
      </Space>

      <Card size="small" title="런타임 설정" variant="borderless">
        <Space wrap>
          <Tag>audit {response.settings.backends.audit_log}</Tag>
          <Tag>metadata {response.settings.backends.document_metadata}</Tag>
          <Tag>queue {response.settings.backends.indexing_queue}</Tag>
          <Tag>max attempts {response.indexing_queue.max_attempts}</Tag>
          {response.indexing_queue.queue_key ? (
            <Tag>{response.indexing_queue.queue_key}</Tag>
          ) : null}
          <Tag>embedding backend {response.settings.backends.embedding}</Tag>
          <Tag>reranker {response.settings.backends.reranker}</Tag>
          <Tag>{response.settings.models.llm}</Tag>
          <Tag>{response.settings.models.embedding}</Tag>
          <Tag>{response.settings.models.reranker}</Tag>
          <Tag>vector {response.settings.models.embedding_vector_size}</Tag>
        </Space>
        <Paragraph className="answer-text">
          {response.indexing_queue.message}
        </Paragraph>
      </Card>

      <List
        className="operations-check-list"
        dataSource={response.checks}
        renderItem={(check) => <OperationsCheckItem check={check} />}
      />

      <Card size="small" title="운영 이벤트" variant="borderless">
        {response.events.length === 0 ? (
          <Empty description="기록된 운영 이벤트가 없습니다." />
        ) : (
          <List
            dataSource={response.events}
            renderItem={(event) => <OperationEventItem event={event} />}
          />
        )}
      </Card>
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

function OperationEventItem({ event }: { event: OperationEvent }) {
  return (
    <List.Item className="audit-event-item">
      <Space direction="vertical" size={6} className="chat-main-stack">
        <Space wrap>
          <Text strong>{event.source}</Text>
          <Tag color={event.severity === "error" ? "red" : "gold"}>
            {event.severity}
          </Tag>
          <Tag>{event.event_type}</Tag>
        </Space>
        <Paragraph className="answer-text">{event.message}</Paragraph>
      </Space>
    </List.Item>
  );
}
