import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosResponse } from 'axios'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Upload,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Progress,
} from 'antd'
import {
  UploadOutlined,
  ReloadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileTextOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  FileWordOutlined,
  FileImageOutlined,
  FileUnknownOutlined,
} from '@ant-design/icons'
import { documentsApi } from '@/api'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Text } = Typography

interface Document {
  id: string
  filename: string
  title: string | null
  author: string | null
  file_size: number
  mime_type: string
  classification: string
  status: string
  chunk_count: number
  page_count: number | null
  version: number
  tags: string[] | null
  department_id: string | null
  project_id: string | null
  uploaded_by: string
  created_at: string
  updated_at: string
  error_message: string | null
}

const statusColors: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  ready: 'success',
  error: 'error',
  deleted: 'default',
}

const statusLabels: Record<string, string> = {
  pending: '대기 중',
  processing: '처리 중',
  ready: '완료',
  error: '오류',
  deleted: '삭제됨',
}

const classificationColors: Record<string, string> = {
  PUBLIC: 'green',
  INTERNAL: 'blue',
  CONFIDENTIAL: 'orange',
  RESTRICTED: 'red',
}

function getFileIcon(mimeType: string) {
  if (mimeType.includes('pdf')) return <FilePdfOutlined style={{ color: '#ff4d4f' }} />
  if (mimeType.includes('word') || mimeType.includes('document'))
    return <FileWordOutlined style={{ color: '#1677ff' }} />
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet'))
    return <FileExcelOutlined style={{ color: '#52c41a' }} />
  if (mimeType.includes('image')) return <FileImageOutlined style={{ color: '#722ed1' }} />
  if (mimeType.includes('text')) return <FileTextOutlined />
  return <FileUnknownOutlined />
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function DocumentsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [form] = Form.useForm()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents', page],
    queryFn: () => documentsApi.list({ page, page_size: 20 }),
    select: (res: AxiosResponse) => res.data,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      message.success('문서가 삭제되었습니다')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: () => {
      message.error('삭제 중 오류가 발생했습니다')
    },
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file, values }: { file: File; values: Record<string, string> }) =>
      documentsApi.upload(file, values),
    onSuccess: () => {
      message.success('문서가 업로드되었습니다')
      setUploadModalOpen(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: () => {
      message.error('업로드 중 오류가 발생했습니다')
    },
  })

  const handleUpload = async (values: Record<string, unknown>) => {
    const file = (values.file as { file?: File })?.file
    if (!file) {
      message.error('파일을 선택하세요')
      return
    }
    uploadMutation.mutate({ file, values: values as Record<string, string> })
  }

  const columns: ColumnsType<Document> = [
    {
      title: '파일명',
      dataIndex: 'filename',
      key: 'filename',
      render: (filename: string, record) => (
        <Space>
          {getFileIcon(record.mime_type)}
          <Text
            style={{ cursor: 'pointer' }}
            onClick={() => navigate(`/documents/${record.id}`)}
          >
            {record.title || filename}
          </Text>
        </Space>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
    },
    {
      title: '보안등급',
      dataIndex: 'classification',
      key: 'classification',
      width: 100,
      render: (cls: string) => <Tag color={classificationColors[cls]}>{cls}</Tag>,
    },
    {
      title: '크기',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: formatFileSize,
    },
    {
      title: '청크',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
      render: (count: number, record) =>
        record.status === 'processing' ? (
          <Progress percent={30} size="small" status="active" />
        ) : (
          count
        ),
    },
    {
      title: '업로드일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '작업',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            icon={<EyeOutlined />}
            size="small"
            onClick={() => navigate(`/documents/${record.id}`)}
          />
          <Button
            icon={<DownloadOutlined />}
            size="small"
            onClick={async () => {
              const res = await documentsApi.download(record.id)
              window.open(res.data.download_url, '_blank')
            }}
          />
          <Popconfirm
            title="이 문서를 삭제하시겠습니까?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ height: '100%' }}>
      <Card
        title="문서 관리"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              새로고침
            </Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadModalOpen(true)}
            >
              업로드
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={data?.items || []}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: 20,
            total: data?.total || 0,
            onChange: setPage,
            showSizeChanger: false,
          }}
        />
      </Card>

      <Modal
        title="문서 업로드"
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleUpload}>
          <Form.Item
            name="file"
            label="파일"
            rules={[{ required: true, message: '파일을 선택하세요' }]}
          >
            <Upload.Dragger
              beforeUpload={() => false}
              maxCount={1}
              accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.hwp,.png,.jpg,.jpeg"
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">클릭하거나 파일을 여기에 드래그하세요</p>
              <p className="ant-upload-hint">
                PDF, DOCX, XLSX, PPTX, TXT, MD, HWP, PNG, JPG 지원
              </p>
            </Upload.Dragger>
          </Form.Item>

          <Form.Item name="title" label="제목 (선택)">
            <Input placeholder="문서 제목" />
          </Form.Item>

          <Form.Item name="classification" label="보안등급" initialValue="INTERNAL">
            <Select>
              <Select.Option value="PUBLIC">공개</Select.Option>
              <Select.Option value="INTERNAL">내부</Select.Option>
              <Select.Option value="CONFIDENTIAL">기밀</Select.Option>
              <Select.Option value="RESTRICTED">극비</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="tags" label="태그 (쉼표 구분)">
            <Input placeholder="태그1, 태그2" />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setUploadModalOpen(false)}>취소</Button>
              <Button type="primary" htmlType="submit" loading={uploadMutation.isPending}>
                업로드
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DocumentsPage
