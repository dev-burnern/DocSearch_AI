import { SendOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  InputNumber,
  List,
  Space,
  Tag,
  Typography,
} from "antd";
import { useMemo, useState } from "react";

import {
  ChatClient,
  ChatResponse,
  createChatApiClient,
} from "../../lib/chat-api";

const { TextArea } = Input;
const { Paragraph, Text, Title } = Typography;

interface ChatWorkspaceProps {
  client?: ChatClient;
  apiKey?: string;
}

export function ChatWorkspace({ client, apiKey: confirmedApiKey }: ChatWorkspaceProps) {
  const chatClient = useMemo(() => client ?? createChatApiClient(), [client]);
  const [apiKey, setApiKey] = useState("");
  const [documentIds, setDocumentIds] = useState("");
  const [topK, setTopK] = useState(5);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const resolvedApiKey = confirmedApiKey ?? apiKey.trim();
  const canSubmit =
    resolvedApiKey.length > 0 && question.trim().length > 0 && !isSubmitting;

  async function submitQuestion() {
    if (!canSubmit) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const nextResponse = await chatClient.ask({
        apiKey: resolvedApiKey,
        question: question.trim(),
        documentIds: parseDocumentIds(documentIds),
        topK,
      });
      setResponse(nextResponse);
    } catch (error) {
      setResponse(null);
      setErrorMessage(
        error instanceof Error ? error.message : "질문 요청에 실패했습니다.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="chat-workspace" aria-label="채팅 작업 화면">
      <Card className="chat-panel" title="질문 설정" variant="borderless">
        <form className="form-stack" onSubmit={(event) => event.preventDefault()}>
          {confirmedApiKey ? null : (
            <>
              <label className="field-label" htmlFor="api-key">
                API Key
              </label>
              <Input.Password
                id="api-key"
                autoComplete="off"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </>
          )}

          <label className="field-label" htmlFor="document-ids">
            문서 ID
          </label>
          <Input
            id="document-ids"
            value={documentIds}
            onChange={(event) => setDocumentIds(event.target.value)}
          />

          <label className="field-label" htmlFor="top-k">
            검색 개수
          </label>
          <InputNumber
            id="top-k"
            min={1}
            max={20}
            value={topK}
            onChange={(value) => setTopK(value ?? 5)}
          />
        </form>
      </Card>

      <Card className="chat-panel chat-main" variant="borderless">
        <form
          className="chat-question-form"
          onSubmit={(event) => {
            event.preventDefault();
            void submitQuestion();
          }}
        >
          <Title level={4} className="section-title">
            답변
          </Title>

          <label className="field-label" htmlFor="question">
            질문
          </label>
          <TextArea
            id="question"
            rows={5}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <Button
            type="primary"
            htmlType="submit"
            icon={<SendOutlined />}
            loading={isSubmitting}
            disabled={!canSubmit}
          >
            질문 보내기
          </Button>

          {errorMessage ? (
            <Alert type="error" message={errorMessage} showIcon />
          ) : null}

          {response ? <AnswerResult response={response} /> : <Empty />}
        </form>
      </Card>
    </section>
  );
}

function AnswerResult({ response }: { response: ChatResponse }) {
  return (
    <section className="answer-result" aria-label="답변 결과">
      <Space direction="vertical" size={14} className="chat-main-stack">
        <Space wrap>
          <Tag color="purple">{response.model}</Tag>
          <Tag color="blue">chunks {response.retrieved_chunk_count}</Tag>
          {response.usage.total_tokens ? (
            <Tag color="green">tokens {response.usage.total_tokens}</Tag>
          ) : null}
        </Space>
        <Paragraph className="answer-text">{response.answer}</Paragraph>
        <List
          className="citation-list"
          dataSource={response.citations}
          renderItem={(citation) => (
            <List.Item>
              <Space direction="vertical" size={4}>
                <Space wrap>
                  <Tag>{citation.citation_id}</Tag>
                  <Text strong>{citation.filename}</Text>
                  <Text type="secondary">score {citation.score.toFixed(2)}</Text>
                  {citation.rerank_score ? (
                    <Text type="secondary">
                      rerank {citation.rerank_score.toFixed(2)}
                    </Text>
                  ) : null}
                </Space>
                <Text>{citation.snippet}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Space>
    </section>
  );
}

function parseDocumentIds(value: string): string[] {
  return value
    .split(",")
    .map((documentId) => documentId.trim())
    .filter(Boolean);
}
