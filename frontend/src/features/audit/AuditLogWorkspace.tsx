import { ReloadOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  List,
  Space,
  Tag,
  Typography,
} from "antd";
import { useMemo, useState } from "react";

import {
  AuditLogClient,
  ChatAuditEvent,
  ChatAuditEventListResponse,
  createAuditLogApiClient,
} from "../../lib/audit-log-api";

const { Paragraph, Text, Title } = Typography;

interface AuditLogWorkspaceProps {
  client?: AuditLogClient;
}

export function AuditLogWorkspace({ client }: AuditLogWorkspaceProps) {
  const auditLogClient = useMemo(
    () => client ?? createAuditLogApiClient(),
    [client],
  );
  const [apiKey, setApiKey] = useState("");
  const [response, setResponse] = useState<ChatAuditEventListResponse | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const canSubmit = apiKey.trim().length > 0 && !isLoading;

  async function loadAuditLogs() {
    if (!canSubmit) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const nextResponse = await auditLogClient.listChatEvents({
        apiKey: apiKey.trim(),
      });
      setResponse(nextResponse);
    } catch (error) {
      setResponse(null);
      setErrorMessage(
        error instanceof Error ? error.message : "감사 로그 조회에 실패했습니다.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  const events = response?.events ?? [];

  return (
    <section className="audit-workspace" aria-label="감사 로그 조회 화면">
      <Card className="chat-panel" title="조회 조건" variant="borderless">
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void loadAuditLogs();
          }}
        >
          <label className="field-label" htmlFor="audit-api-key">
            API Key
          </label>
          <Input.Password
            id="audit-api-key"
            autoComplete="off"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
          />
          <Button
            type="primary"
            htmlType="submit"
            icon={<ReloadOutlined />}
            loading={isLoading}
            disabled={!canSubmit}
          >
            로그 조회
          </Button>
        </form>
      </Card>

      <Card className="chat-panel audit-main" variant="borderless">
        <Space direction="vertical" size={16} className="chat-main-stack">
          <Space className="audit-heading" align="start">
            <div>
              <Title level={4} className="section-title">
                채팅 감사 로그
              </Title>
              <Paragraph className="audit-subtitle">
                워크스페이스별 질문, 답변, 출처 기록을 확인합니다.
              </Paragraph>
            </div>
            <Tag color="blue">total {response?.total ?? 0}</Tag>
          </Space>

          {errorMessage ? (
            <Alert type="error" message={errorMessage} showIcon />
          ) : null}

          {response && events.length === 0 ? (
            <Empty description="아직 감사 로그가 없습니다." />
          ) : null}

          {events.length > 0 ? (
            <List
              className="audit-event-list"
              dataSource={events}
              renderItem={(event) => <AuditLogEventItem event={event} />}
            />
          ) : null}
        </Space>
      </Card>
    </section>
  );
}

function AuditLogEventItem({ event }: { event: ChatAuditEvent }) {
  return (
    <List.Item className="audit-event-item">
      <Space direction="vertical" size={10} className="chat-main-stack">
        <Space wrap>
          <Tag color="purple">{event.model}</Tag>
          <Tag color="green">{event.workspace_name}</Tag>
          {event.total_tokens ? (
            <Tag color="blue">tokens {event.total_tokens}</Tag>
          ) : null}
          <Tag>chunks {event.retrieved_chunk_count}</Tag>
          <Tag>rerank {event.rerank_top_k}</Tag>
        </Space>
        <Text strong>{event.question}</Text>
        <Paragraph className="answer-text">{event.answer_preview}</Paragraph>
        <Space wrap>
          <Text type="secondary">{formatDateTime(event.occurred_at)}</Text>
          <Text type="secondary">request {event.request_id}</Text>
          {event.document_ids?.map((documentId) => (
            <Tag key={documentId}>{documentId}</Tag>
          ))}
        </Space>
        {event.citations.length > 0 ? (
          <Space wrap>
            {event.citations.map((citation) => (
              <Tag key={`${event.event_id}-${citation.citation_id}`}>
                {citation.filename}
              </Tag>
            ))}
          </Space>
        ) : null}
      </Space>
    </List.Item>
  );
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
