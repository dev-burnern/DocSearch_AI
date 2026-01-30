import React, { useState, useRef, useEffect, ChangeEvent, KeyboardEvent } from 'react'
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Spin,
  Tag,
  Collapse,
  Empty,
  Tooltip,
} from 'antd'
import {
  SendOutlined,
  ClearOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { chatApi } from '@/api'
import { useChatStore, type ChatMessage, type Citation } from '@/stores/chat'

const { Text, Paragraph } = Typography
const { TextArea } = Input

function ChatPage() {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, isLoading, addMessage, setLoading, clearMessages } = useChatStore()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const query = input.trim()
    setInput('')

    // Add user message
    addMessage({ role: 'user', content: query })
    setLoading(true)

    try {
      const response = await chatApi.chat({
        query,
        top_k: 50,
        top_n: 5,
        use_rerank: true,
        use_hybrid: true,
      })

      const { answer, citations, metrics } = response.data

      addMessage({
        role: 'assistant',
        content: answer,
        citations,
        metrics,
      })
    } catch (error) {
      addMessage({
        role: 'assistant',
        content: '죄송합니다. 응답 생성 중 오류가 발생했습니다. 다시 시도해 주세요.',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Card
        title="AI 문서 검색 채팅"
        extra={
          <Button icon={<ClearOutlined />} onClick={clearMessages}>
            대화 초기화
          </Button>
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
        styles={{ body: { flex: 1, overflow: 'auto', padding: '16px 24px' } }}
      >
        {messages.length === 0 ? (
          <Empty
            description={
              <Space direction="vertical">
                <Text>문서에 대해 질문해 보세요</Text>
                <Text type="secondary">
                  예: "프로젝트 일정에 대해 알려줘", "계약서의 주요 조건은?"
                </Text>
              </Space>
            }
            style={{ marginTop: 100 }}
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.map((msg: ChatMessage) => (
              <React.Fragment key={msg.id}>
                <MessageBubble message={msg} />
              </React.Fragment>
            ))}
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
                <Spin tip="응답 생성 중..." />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </Card>

      <Card size="small" style={{ marginTop: 16 }}>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={input}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="질문을 입력하세요... (Shift+Enter로 줄바꿈)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={isLoading}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isLoading}
            style={{ height: 'auto' }}
          >
            전송
          </Button>
        </Space.Compact>
      </Card>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      <div
        className={`chat-message ${message.role}`}
        style={{
          maxWidth: isUser ? '70%' : '85%',
        }}
      >
        <ReactMarkdown>{message.content}</ReactMarkdown>

        {message.citations && message.citations.length > 0 && (
          <Collapse
            size="small"
            style={{ marginTop: 12 }}
            items={[
              {
                key: 'citations',
                label: (
                  <Space>
                    <FileTextOutlined />
                    <Text>참조 문서 ({message.citations.length})</Text>
                  </Space>
                ),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {message.citations.map((cite, idx) => (
                      <React.Fragment key={idx}>
                        <CitationItem citation={cite} index={idx + 1} />
                      </React.Fragment>
                    ))}
                  </Space>
                ),
              },
            ]}
          />
        )}

        {message.metrics && (
          <div style={{ marginTop: 8 }}>
            <Tooltip title="응답 시간">
              <Tag icon={<ClockCircleOutlined />} color="blue">
                {message.metrics.total_ms?.toFixed(0)}ms
              </Tag>
            </Tooltip>
          </div>
        )}
      </div>
    </div>
  )
}

function CitationItem({ citation, index }: { citation: Citation; index: number }) {
  return (
    <Card size="small">
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Space>
          <Tag color="blue">[{index}]</Tag>
          <Text strong>{citation.source}</Text>
          {citation.page && <Tag>페이지 {citation.page}</Tag>}
          {citation.sheet && <Tag>시트: {citation.sheet}</Tag>}
          <Tag color="green">유사도: {(citation.score * 100).toFixed(1)}%</Tag>
        </Space>
        <Paragraph
          ellipsis={{ rows: 3, expandable: true }}
          style={{ marginBottom: 0, fontSize: 13 }}
        >
          {citation.text}
        </Paragraph>
      </Space>
    </Card>
  )
}

export default ChatPage
