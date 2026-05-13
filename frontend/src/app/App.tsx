import { useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Divider,
  Input,
  InputNumber,
  Layout,
  List,
  Space,
  Tag,
  Typography,
} from "antd";

const { Content, Header } = Layout;
const { Paragraph, Text, Title } = Typography;

const API_PREFIX = "/api";
const WORKSPACE_HEADER = "local-dev-key";

type UploadedDocument = {
  document_id: string;
  filename: string;
  parser: string;
  character_count: number;
  indexing_status: string;
  chunk_count: number;
};

type ChatCitation = {
  citation_id: number;
  document_id: string;
  filename: string;
  chunk_index: number;
  score: number;
  rerank_score?: number;
  snippet: string;
};

type ChatResponse = {
  answer: string;
  model: string;
  citations: ChatCitation[];
  usage: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  retrieved_chunk_count: number;
};

async function readApiError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (detail?.message) {
      return detail.message;
    }

    if (detail?.code) {
      return detail.code;
    }
  } catch {
    return response.statusText;
  }

  return response.statusText;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

export default function App() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState<number | null>(5);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);

  const selectedDocumentNames = useMemo(
    () =>
      documents
        .filter((document) => selectedDocumentIds.includes(document.document_id))
        .map((document) => document.filename),
    [documents, selectedDocumentIds],
  );

  const requestHeaders = useMemo(
    () => ({
      "X-API-Key": WORKSPACE_HEADER,
    }),
    [],
  );

  async function uploadDocument(file: File) {
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_PREFIX}/v1/documents`, {
        method: "POST",
        headers: requestHeaders,
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const uploadedDocument = (await response.json()) as UploadedDocument;

      setDocuments((currentDocuments) => [
        uploadedDocument,
        ...currentDocuments.filter(
          (document) => document.document_id !== uploadedDocument.document_id,
        ),
      ]);
      setSelectedDocumentIds((currentIds) => [
        uploadedDocument.document_id,
        ...currentIds.filter((documentId) => documentId !== uploadedDocument.document_id),
      ]);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function submitQuestion() {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      setChatError("Question is required.");
      return;
    }

    setIsAnswering(true);
    setChatError(null);

    try {
      const response = await fetch(`${API_PREFIX}/v1/chat`, {
        method: "POST",
        headers: {
          ...requestHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          document_ids:
            selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
          top_k: topK ?? undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      setChatResponse((await response.json()) as ChatResponse);
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Chat request failed.");
      setChatResponse(null);
    } finally {
      setIsAnswering(false);
    }
  }

  function toggleDocument(documentId: string, checked: boolean) {
    setSelectedDocumentIds((currentIds) => {
      if (checked) {
        return [...currentIds, documentId];
      }

      return currentIds.filter((currentId) => currentId !== documentId);
    });
  }

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Space direction="vertical" size={0}>
          <Title level={4} className="app-title">
            DocSearch AI
          </Title>
          <Text type="secondary">Document search and cited answers</Text>
        </Space>
      </Header>

      <Content className="app-content">
        <section className="workspace-grid">
          <div className="tool-panel documents-panel">
            <div className="panel-heading">
              <Title level={5}>Documents</Title>
              <Button
                loading={isUploading}
                onClick={() => fileInputRef.current?.click()}
                type="primary"
              >
                Upload
              </Button>
            </div>

            <input
              ref={fileInputRef}
              className="hidden-file-input"
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (file) {
                  void uploadDocument(file);
                }
              }}
              type="file"
            />

            {uploadError && (
              <Alert
                message={uploadError}
                showIcon
                type="error"
                className="inline-alert"
              />
            )}

            <List
              dataSource={documents}
              locale={{ emptyText: "No uploaded documents" }}
              renderItem={(document) => (
                <List.Item
                  actions={[
                    <Checkbox
                      checked={selectedDocumentIds.includes(document.document_id)}
                      key="select"
                      onChange={(event) =>
                        toggleDocument(document.document_id, event.target.checked)
                      }
                    >
                      Use
                    </Checkbox>,
                  ]}
                >
                  <List.Item.Meta
                    title={<Text strong>{document.filename}</Text>}
                    description={
                      <Space wrap size={[8, 4]}>
                        <Tag>{document.parser}</Tag>
                        <Tag color="green">{document.indexing_status}</Tag>
                        <Text type="secondary">
                          {formatNumber(document.character_count)} chars
                        </Text>
                        <Text type="secondary">{document.chunk_count} chunks</Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </div>

          <div className="tool-panel chat-panel">
            <div className="panel-heading">
              <Title level={5}>Chat</Title>
              <Space align="center" size={8}>
                <Text type="secondary">Top K</Text>
                <InputNumber
                  min={1}
                  max={20}
                  value={topK}
                  onChange={setTopK}
                  className="top-k-input"
                />
              </Space>
            </div>

            <Input.TextArea
              autoSize={{ minRows: 4, maxRows: 8 }}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onPressEnter={(event) => {
                if (event.metaKey || event.ctrlKey) {
                  void submitQuestion();
                }
              }}
              placeholder="Ask a question about the uploaded documents"
            />

            <div className="chat-actions">
              <Text type="secondary" className="selected-documents">
                {selectedDocumentNames.length > 0
                  ? selectedDocumentNames.join(", ")
                  : "All workspace documents"}
              </Text>
              <Button
                loading={isAnswering}
                onClick={() => void submitQuestion()}
                type="primary"
              >
                Ask
              </Button>
            </div>

            {chatError && (
              <Alert
                message={chatError}
                showIcon
                type="error"
                className="inline-alert"
              />
            )}

            {chatResponse && (
              <div className="answer-panel">
                <Paragraph className="answer-text">{chatResponse.answer}</Paragraph>

                <Space wrap size={[8, 8]}>
                  <Tag color="blue">{chatResponse.model}</Tag>
                  <Tag>{chatResponse.retrieved_chunk_count} chunks</Tag>
                  {chatResponse.usage.total_tokens !== undefined && (
                    <Tag>{chatResponse.usage.total_tokens} tokens</Tag>
                  )}
                </Space>

                <Divider />

                <List
                  dataSource={chatResponse.citations}
                  locale={{ emptyText: "No citations" }}
                  renderItem={(citation) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space wrap size={[8, 4]}>
                            <Text strong>[{citation.citation_id}]</Text>
                            <Text strong>{citation.filename}</Text>
                            <Tag>chunk {citation.chunk_index}</Tag>
                            <Tag color="gold">
                              score {citation.score.toFixed(3)}
                            </Tag>
                            {citation.rerank_score !== undefined && (
                              <Tag color="purple">
                                rerank {citation.rerank_score.toFixed(3)}
                              </Tag>
                            )}
                          </Space>
                        }
                        description={
                          <Text type="secondary">{citation.snippet}</Text>
                        }
                      />
                    </List.Item>
                  )}
                />
              </div>
            )}
          </div>
        </section>
      </Content>
    </Layout>
  );
}
