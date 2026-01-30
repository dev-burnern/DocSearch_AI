import { useState, ChangeEvent } from 'react'
import { Card, Input, Button, Table, Space, Tag, Typography, Empty } from 'antd'
import { SearchOutlined, FileTextOutlined } from '@ant-design/icons'
import { searchApi } from '@/api'
import type { ColumnsType } from 'antd/es/table'

const { Text, Paragraph } = Typography

interface SearchHit {
  chunk_id: string
  doc_id: string
  score: number
  text: string
  source: string
  page?: number
  sheet?: string
  slide?: number
  chunk_index: number
  heading?: string
  highlight?: string
}

interface SearchResult {
  query: string
  hits: SearchHit[]
  total: number
  metrics: {
    embed_ms: number
    search_ms: number
    rerank_ms: number
    total_ms: number
  }
}

function SearchPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SearchResult | null>(null)

  const handleSearch = async () => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const response = await searchApi.search({
        query: query.trim(),
        top_k: 50,
        top_n: 10,
        use_rerank: true,
        use_hybrid: true,
      })
      setResult(response.data)
    } catch {
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const columns: ColumnsType<SearchHit> = [
    {
      title: '#',
      key: 'index',
      width: 50,
      render: (_, __, index) => index + 1,
    },
    {
      title: '유사도',
      dataIndex: 'score',
      key: 'score',
      width: 100,
      render: (score: number) => (
        <Tag color={score > 0.8 ? 'green' : score > 0.6 ? 'blue' : 'default'}>
          {(score * 100).toFixed(1)}%
        </Tag>
      ),
      sorter: (a, b) => b.score - a.score,
    },
    {
      title: '문서',
      dataIndex: 'source',
      key: 'source',
      width: 200,
      render: (source: string, record) => (
        <Space direction="vertical" size="small">
          <Space>
            <FileTextOutlined />
            <Text strong ellipsis style={{ maxWidth: 150 }}>
              {source}
            </Text>
          </Space>
          <Space size="small">
            {record.page && <Tag>p.{record.page}</Tag>}
            {record.sheet && <Tag>{record.sheet}</Tag>}
            {record.heading && <Tag color="purple">{record.heading}</Tag>}
          </Space>
        </Space>
      ),
    },
    {
      title: '내용',
      dataIndex: 'text',
      key: 'text',
      render: (text: string, record) => (
        <Paragraph
          ellipsis={{ rows: 3, expandable: true }}
          style={{ marginBottom: 0 }}
        >
          {record.highlight ? (
            <span dangerouslySetInnerHTML={{ __html: record.highlight.replace(/\*\*(.*?)\*\*/g, '<mark>$1</mark>') }} />
          ) : (
            text
          )}
        </Paragraph>
      ),
    },
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            placeholder="검색어를 입력하세요..."
            value={query}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
            onPressEnter={handleSearch}
            size="large"
            prefix={<SearchOutlined />}
          />
          <Button
            type="primary"
            size="large"
            onClick={handleSearch}
            loading={loading}
          >
            검색
          </Button>
        </Space.Compact>
      </Card>

      <Card
        title={
          result && (
            <Space>
              <Text>검색 결과</Text>
              <Tag color="blue">{result.total}건</Tag>
              <Tag color="green">{result.metrics.total_ms.toFixed(0)}ms</Tag>
            </Space>
          )
        }
        style={{ flex: 1, overflow: 'hidden' }}
        styles={{ body: { height: 'calc(100% - 57px)', overflow: 'auto' } }}
      >
        {result ? (
          <Table
            dataSource={result.hits}
            columns={columns}
            rowKey="chunk_id"
            pagination={false}
            size="middle"
          />
        ) : (
          <Empty
            description={
              <Space direction="vertical">
                <Text>검색어를 입력하여 문서를 검색하세요</Text>
                <Text type="secondary">
                  하이브리드 검색 (의미 + 키워드)으로 정확한 결과를 찾아드립니다
                </Text>
              </Space>
            }
            style={{ marginTop: 100 }}
          />
        )}
      </Card>
    </div>
  )
}

export default SearchPage
