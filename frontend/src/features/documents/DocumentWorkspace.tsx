import {
  DeleteOutlined,
  SearchOutlined,
  SyncOutlined,
  UnorderedListOutlined,
  UploadOutlined,
} from "@ant-design/icons";
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
  DocumentListResponse,
  DocumentRecord,
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
  apiKey?: string;
}

export function DocumentWorkspace({
  documentClient,
  searchClient,
  apiKey: confirmedApiKey,
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
  const [documentList, setDocumentList] =
    useState<DocumentListResponse | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [isListing, setIsListing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(
    null,
  );
  const [reindexingDocumentId, setReindexingDocumentId] = useState<string | null>(
    null,
  );

  const trimmedApiKey = confirmedApiKey ?? apiKey.trim();
  const canUpload = trimmedApiKey.length > 0 && file !== null && !isUploading;
  const canSearch =
    trimmedApiKey.length > 0 && query.trim().length > 0 && !isSearching;
  const canList = trimmedApiKey.length > 0 && !isListing;

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

  async function listDocuments() {
    if (!canList) {
      return;
    }

    setIsListing(true);
    setListError(null);

    try {
      const nextList = await resolvedDocumentClient.listDocuments({
        apiKey: trimmedApiKey,
      });
      setDocumentList(nextList);
      setActionError(null);
    } catch (error) {
      setDocumentList(null);
      setListError(
        error instanceof Error ? error.message : "문서 목록 조회에 실패했습니다.",
      );
    } finally {
      setIsListing(false);
    }
  }

  async function deleteDocument(record: DocumentRecord) {
    if (!trimmedApiKey) {
      return;
    }

    setDeletingDocumentId(record.document_id);
    setActionError(null);

    try {
      await resolvedDocumentClient.deleteDocument({
        apiKey: trimmedApiKey,
        documentId: record.document_id,
      });
      setDocumentList((current) => removeDocument(current, record.document_id));
      setDocumentIds((current) => removeDocumentId(current, record.document_id));
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "문서 삭제에 실패했습니다.",
      );
    } finally {
      setDeletingDocumentId(null);
    }
  }

  async function reindexDocument(record: DocumentRecord) {
    if (!trimmedApiKey) {
      return;
    }

    setReindexingDocumentId(record.document_id);
    setActionError(null);

    try {
      const updatedRecord = await resolvedDocumentClient.reindexDocument({
        apiKey: trimmedApiKey,
        documentId: record.document_id,
      });
      setDocumentList((current) => upsertDocument(current, updatedRecord));
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "문서 재인덱싱에 실패했습니다.",
      );
    } finally {
      setReindexingDocumentId(null);
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
          {confirmedApiKey ? null : (
            <>
              <label className="field-label" htmlFor="document-api-key">
                API Key
              </label>
              <Input.Password
                id="document-api-key"
                autoComplete="off"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </>
          )}

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
        <Space direction="vertical" size={20} className="chat-main-stack">
          <section className="document-list-section">
            <Space className="audit-heading" align="start" wrap>
              <div>
                <Title level={4} className="section-title">
                  업로드 문서
                </Title>
                <Text type="secondary">워크스페이스 문서 메타데이터</Text>
              </div>
              <Button
                type="default"
                icon={<UnorderedListOutlined />}
                loading={isListing}
                disabled={!canList}
                onClick={() => void listDocuments()}
              >
                문서 목록 조회
              </Button>
            </Space>

            {listError ? (
              <Alert type="error" message={listError} showIcon />
            ) : null}

            {actionError ? (
              <Alert type="error" message={actionError} showIcon />
            ) : null}

            {documentList?.documents.length === 0 ? (
              <Empty description="업로드된 문서가 없습니다." />
            ) : null}

            {documentList && documentList.documents.length > 0 ? (
              <DocumentList
                result={documentList}
                deletingDocumentId={deletingDocumentId}
                reindexingDocumentId={reindexingDocumentId}
                onDelete={(record) => void deleteDocument(record)}
                onReindex={(record) => void reindexDocument(record)}
              />
            ) : null}
          </section>

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
        </Space>
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
        {result.indexing_error ? (
          <Alert type="error" message={result.indexing_error} showIcon />
        ) : null}
        <Paragraph className="answer-text">{result.text_preview}</Paragraph>
      </Space>
    </section>
  );
}

interface DocumentListProps {
  result: DocumentListResponse;
  deletingDocumentId: string | null;
  reindexingDocumentId: string | null;
  onDelete(record: DocumentRecord): void;
  onReindex(record: DocumentRecord): void;
}

function DocumentList({
  result,
  deletingDocumentId,
  reindexingDocumentId,
  onDelete,
  onReindex,
}: DocumentListProps) {
  return (
    <section className="document-result" aria-label="업로드 문서 목록">
      <Space direction="vertical" size={12} className="chat-main-stack">
        <Tag color="blue">total {result.total}</Tag>
        <List
          className="audit-event-list"
          dataSource={result.documents}
          renderItem={(record) => (
            <DocumentListItem
              record={record}
              isDeleting={deletingDocumentId === record.document_id}
              isReindexing={reindexingDocumentId === record.document_id}
              onDelete={onDelete}
              onReindex={onReindex}
            />
          )}
        />
      </Space>
    </section>
  );
}

interface DocumentListItemProps {
  record: DocumentRecord;
  isDeleting: boolean;
  isReindexing: boolean;
  onDelete(record: DocumentRecord): void;
  onReindex(record: DocumentRecord): void;
}

function DocumentListItem({
  record,
  isDeleting,
  isReindexing,
  onDelete,
  onReindex,
}: DocumentListItemProps) {
  return (
    <List.Item className="audit-event-item">
      <Space direction="vertical" size={6} className="chat-main-stack">
        <Space wrap>
          <Text strong>{record.filename}</Text>
          <Tag color="green">{record.indexing_status}</Tag>
          <Tag color="blue">chunks {record.chunk_count}</Tag>
          <Tag>{record.parser}</Tag>
          <Text type="secondary">{formatUploadedAt(record.uploaded_at)}</Text>
        </Space>
        <Text copyable>{record.document_id}</Text>
        <Text type="secondary">{record.workspace_name}</Text>
        {record.indexing_error ? (
          <Alert type="error" message={record.indexing_error} showIcon />
        ) : null}
        <Paragraph className="answer-text">{record.text_preview}</Paragraph>
        <Space wrap>
          <Button
            size="small"
            icon={<SyncOutlined />}
            loading={isReindexing}
            disabled={isDeleting}
            onClick={() => onReindex(record)}
          >
            재인덱싱
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={isDeleting}
            disabled={isReindexing}
            onClick={() => onDelete(record)}
          >
            삭제
          </Button>
        </Space>
      </Space>
    </List.Item>
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

function formatUploadedAt(value: string): string {
  const uploadedAt = new Date(value);

  if (Number.isNaN(uploadedAt.getTime())) {
    return value;
  }

  return uploadedAt.toLocaleString("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function parseDocumentIds(value: string): string[] {
  return value
    .split(",")
    .map((documentId) => documentId.trim())
    .filter(Boolean);
}

function removeDocument(
  current: DocumentListResponse | null,
  documentId: string,
): DocumentListResponse | null {
  if (!current) {
    return current;
  }

  const documents = current.documents.filter(
    (record) => record.document_id !== documentId,
  );
  return {
    documents,
    total: documents.length,
  };
}

function upsertDocument(
  current: DocumentListResponse | null,
  record: DocumentRecord,
): DocumentListResponse | null {
  if (!current) {
    return {
      documents: [record],
      total: 1,
    };
  }

  const exists = current.documents.some(
    (document) => document.document_id === record.document_id,
  );
  const documents = exists
    ? current.documents.map((document) =>
        document.document_id === record.document_id ? record : document,
      )
    : [record, ...current.documents];

  return {
    documents,
    total: documents.length,
  };
}

function removeDocumentId(value: string, documentId: string): string {
  return parseDocumentIds(value)
    .filter((currentDocumentId) => currentDocumentId !== documentId)
    .join(", ");
}
