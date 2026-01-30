import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { AxiosResponse } from 'axios'
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Table,
  Skeleton,
  Alert,
} from 'antd'
import { ArrowLeftOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import { documentsApi } from '@/api'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'

const { Title, Paragraph } = Typography

interface Chunk {
  id: string
  chunk_index: number
  text: string
  page_number: number | null
  sheet_name: string | null
  heading: string | null
}

const statusColors: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  ready: 'success',
  error: 'error',
}

function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.get(id!, true),
    select: (res: AxiosResponse) => res.data,
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 10 }} />
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card>
        <Alert
          message="문서를 찾을 수 없습니다"
          type="error"
          action={
            <Button onClick={() => navigate('/documents')}>목록으로</Button>
          }
        />
      </Card>
    )
  }

  const chunkColumns: ColumnsType<Chunk> = [
    {
      title: '#',
      dataIndex: 'chunk_index',
      key: 'chunk_index',
      width: 60,
    },
    {
      title: '위치',
      key: 'location',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.page_number && <Tag>페이지 {record.page_number}</Tag>}
          {record.sheet_name && <Tag color="blue">{record.sheet_name}</Tag>}
          {record.heading && <Tag color="purple">{record.heading}</Tag>}
        </Space>
      ),
    },
    {
      title: '내용',
      dataIndex: 'text',
      key: 'text',
      render: (text: string) => (
        <Paragraph ellipsis={{ rows: 3, expandable: true }} style={{ marginBottom: 0 }}>
          {text}
        </Paragraph>
      ),
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>
            목록
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            새로고침
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={async () => {
              const res = await documentsApi.download(data.id)
              window.open(res.data.download_url, '_blank')
            }}
          >
            다운로드
          </Button>
        </Space>

        <Title level={4}>{data.title || data.filename}</Title>

        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="파일명">{data.filename}</Descriptions.Item>
          <Descriptions.Item label="상태">
            <Tag color={statusColors[data.status]}>{data.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="보안등급">
            <Tag
              color={
                data.classification === 'public'
                  ? 'green'
                  : data.classification === 'internal'
                  ? 'blue'
                  : data.classification === 'confidential'
                  ? 'orange'
                  : 'red'
              }
            >
              {data.classification}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="파일 크기">
            {(data.file_size / 1024 / 1024).toFixed(2)} MB
          </Descriptions.Item>
          <Descriptions.Item label="MIME 타입">{data.mime_type}</Descriptions.Item>
          <Descriptions.Item label="청크 수">{data.chunk_count}</Descriptions.Item>
          <Descriptions.Item label="페이지 수">{data.page_count || '-'}</Descriptions.Item>
          <Descriptions.Item label="버전">{data.version}</Descriptions.Item>
          <Descriptions.Item label="업로드일">
            {dayjs(data.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          <Descriptions.Item label="수정일">
            {dayjs(data.updated_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          {data.tags && data.tags.length > 0 && (
            <Descriptions.Item label="태그" span={2}>
              <Space>
                {data.tags.map((tag: string) => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          )}
          {data.error_message && (
            <Descriptions.Item label="오류 메시지" span={2}>
              <Alert message={data.error_message} type="error" />
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {data.processing_jobs && data.processing_jobs.length > 0 && (
        <Card title="처리 이력">
          <Table
            dataSource={data.processing_jobs}
            rowKey="id"
            pagination={false}
            size="small"
            columns={[
              {
                title: '작업 유형',
                dataIndex: 'job_type',
                key: 'job_type',
              },
              {
                title: '상태',
                dataIndex: 'status',
                key: 'status',
                render: (status: string) => <Tag color={statusColors[status]}>{status}</Tag>,
              },
              {
                title: '진행률',
                dataIndex: 'progress',
                key: 'progress',
                render: (progress: number) => `${progress}%`,
              },
              {
                title: '시작',
                dataIndex: 'started_at',
                key: 'started_at',
                render: (date: string) =>
                  date ? dayjs(date).format('MM-DD HH:mm:ss') : '-',
              },
              {
                title: '완료',
                dataIndex: 'completed_at',
                key: 'completed_at',
                render: (date: string) =>
                  date ? dayjs(date).format('MM-DD HH:mm:ss') : '-',
              },
            ]}
          />
        </Card>
      )}

      {data.chunks && data.chunks.length > 0 && (
        <Card title={`청크 목록 (${data.chunks.length}개)`}>
          <Table
            dataSource={data.chunks}
            columns={chunkColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      )}
    </div>
  )
}

export default DocumentDetailPage
