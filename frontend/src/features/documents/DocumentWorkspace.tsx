import { SearchOutlined, UploadOutlined } from "@ant-design/icons";
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
  DocumentClient,
  DocumentUploadResponse,
  createDocumentApiClient,
} from "../../lib/document-api";
import {
  SearchClient,
  SearchResponse,
  SearchResultChunk,
  createSearchApiClient,
} from "../../lib/search-api";

const { Paragraph, Text, Title } = Typography;

interface DocumentWorkspaceProps {
  documentClient?: DocumentClient;
  searchClient?: SearchClient;
}

export function DocumentWorkspace({
  documentClient,
  searchClient,
}: DocumentWorkspaceProps) {
  const resolvedDocumentClient = useMemo(
    () => documentClient ?? createDocumentApiClient(),
    [documentClient],
  );
  const resolvedSearchClient = useMemo(
    () => searchClient ?? createSearchApiClient(),
    [searchClient],
  );
  const [apiKey, setApiKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] =
    useState<DocumentUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [documentIds, setDocumentIds] = useState("");
  const [limit, setLimit] = useState(5);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const trimmedApiKey = apiKey.trim();
  const canUpload = trimmedApiKey.length > 0 && file !== null && !isUploading;
  const canSearch =
    trimmedApiKey.length > 0 && query.trim().length > 0 && !isSearching;

  async function uploadDocument() {
    if (!canUpload || file === null) {
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const nextResult = await resolvedDocumentClient.uploadDocument({
        apiKey: trimmedApiKey,
        file,
      });
      setUploadResult(nextResult);
      setDocumentIds((current) => current || nextResult.document_id);
    } catch (error) {
      setUploadResult(null);
      setUploadError(
        error instanceof Error ? error.message : "문서 업로드에 실패했습니다.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function searchDocuments() {
    if (!canSearch) {
      return;
    }

    setIsSearching(true);
    setSearchError(null);

    try {
      const nextResult = await resolvedSearchClient.searchDocuments({
        apiKey: trimmedApiKey,
        query: query.trim(),
        documentIds: parseDocumentIds(documentIds),
        limit,
      });
      setSearchResult(nextResult);
    } catch (error) {
      setSearchResult(null);
      setSearchError(
        error instanceof Error ? error.message : "문서 검색에 실패했습니다.",
      );
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <section className="document-workspace" aria-label="문서 작업 화면">
      <Card className="chat-panel" variant="borderless">
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault();
            void uploadDocument();
          }}
        >
          <Title level={4} className="section-title">
            문서 업로드
          </Title>
          <label className="field-label" htmlFor="document-api-key">
            API Key
          </label>
          <Input.Password
            id="document-api-key"
            autoComplete="off"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
          />

          <label className="field-label" htmlFor="document-file">
            문서 파일
          </label>
          <Input
            id="document-file"
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />

          <Button
            type="primary"
            htmlType="submit"
            icon={<UploadOutlined />}
            loading={isUploading}
            disabled={!canUpload}
          >
            문서 업로드
          </Button>

          {uploadError ? (
            <Alert type="error" message={uploadError} showIcon />
          ) : null}

          {uploadResult ? <UploadResult result={uploadResult} /> : null}
        </form>
      </Card>

      <Card className="chat-panel document-main" variant="borderless">
        <form
          className="document-search-form"
          onSubmit={(event) => {
            event.preventDefault();
            void searchDocuments();
          }}
        >
          <Title level={4} className="section-title">
            문서 검색
          </Title>
          <label className="field-label" htmlFor="search-query">
            검색어
          </label>
          <Input
            id="search-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          <label className="field-label" htmlFor="search-document-ids">
            검색 문서 ID
          </label>
          <Input
            id="search-document-ids"
            value={documentIds}
            onChange={(event) => setDocumentIds(event.target.value)}
          />

          <label className="field-label" htmlFor="search-limit">
            검색 개수
          </label>
          <InputNumber
            id="search-limit"
            min={1}
            max={20}
            value={limit}
            onChange={(value) => setLimit(value ?? 5)}
          />

          <Button
            type="primary"
            htmlType="submit"
            icon={<SearchOutlined />}
            loading={isSearching}
            disabled={!canSearch}
          >
            문서 검색
          </Button>

          {searchError ? (
            <Alert type="error" message={searchError} showIcon />
          ) : null}

          {searchResult?.results.length === 0 ? (
            <Empty description="검색 결과가 없습니다." />
          ) : null}

          {searchResult && searchResult.results.length > 0 ? (
            <SearchResults result={searchResult} />
          ) : null}
        </form>
      </Card>
    </section>
  );
}

function UploadResult({ result }: { result: DocumentUploadResponse }) {
  return (
    <section className="document-result" aria-label="업로드 결과">
      <Space direction="vertical" size={8} className="chat-main-stack">
        <Space wrap>
          <Tag color="green">{result.indexing_status}</Tag>
          <Tag color="blue">chunks {result.chunk_count}</Tag>
          <Tag>{result.parser}</Tag>
        </Space>
        <Text strong>{result.filename}</Text>
        <Text copyable>{result.document_id}</Text>
        <Text type="secondary">{result.workspace_name}</Text>
        <Paragraph className="answer-text">{result.text_preview}</Paragraph>
      </Space>
    </section>
  );
}

function SearchResults({ result }: { result: SearchResponse }) {
  return (
    <section className="document-result" aria-label="검색 결과">
      <Space direction="vertical" size={12} className="chat-main-stack">
        <Tag color="blue">total {result.total}</Tag>
        <List
          className="audit-event-list"
          dataSource={result.results}
          renderItem={(chunk) => <SearchResultItem chunk={chunk} />}
        />
      </Space>
    </section>
  );
}

function SearchResultItem({ chunk }: { chunk: SearchResultChunk }) {
  return (
    <List.Item className="audit-event-item">
      <Space direction="vertical" size={6} className="chat-main-stack">
        <Space wrap>
          <Text strong>{chunk.filename}</Text>
          <Tag>{chunk.document_id}</Tag>
          <Tag>{chunk.parser}</Tag>
          <Text type="secondary">chunk {chunk.chunk_index}</Text>
          <Text type="secondary">score {chunk.score.toFixed(2)}</Text>
        </Space>
        <Text>{chunk.snippet}</Text>
      </Space>
    </List.Item>
  );
}

function parseDocumentIds(value: string): string[] {
  return value
    .split(",")
    .map((documentId) => documentId.trim())
    .filter(Boolean);
}
