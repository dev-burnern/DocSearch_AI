import { useQuery } from '@tanstack/react-query'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import type { AxiosResponse } from 'axios'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Menu,
  Typography,
  Space,
  Tag,
} from 'antd'
import {
  DashboardOutlined,
  UserOutlined,
  FileOutlined,
  SearchOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { adminApi } from '@/api'
import dayjs from 'dayjs'

const { Title } = Typography

function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => adminApi.getStats(),
    select: (res: AxiosResponse) => res.data,
  })

  if (isLoading) {
    return <Card loading />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Title level={4}>대시보드</Title>

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="전체 문서"
              value={data?.documents.total || 0}
              prefix={<FileOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="처리 완료"
              value={data?.documents.ready || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="처리 중"
              value={data?.documents.processing || 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="오류"
              value={data?.documents.error || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Card title="사용자">
            <Statistic
              title="활성 사용자"
              value={data?.users.active || 0}
              suffix={`/ ${data?.users.total || 0}`}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="벡터 DB">
            <Space direction="vertical">
              <Statistic
                title="총 벡터 수"
                value={data?.vector_store.points_count || 0}
              />
              <Tag color={data?.vector_store.status === 'green' ? 'success' : 'warning'}>
                {data?.vector_store.status || 'unknown'}
              </Tag>
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="LLM 서비스">
            <Space direction="vertical">
              <Tag color={data?.llm.healthy ? 'success' : 'error'}>
                {data?.llm.healthy ? '정상' : '비정상'}
              </Tag>
              <div>
                사용 가능 모델: {data?.llm.models?.join(', ') || '-'}
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="총 청크 수">
        <Statistic value={data?.documents.total_chunks || 0} />
      </Card>
    </div>
  )
}

function AdminUsers() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => adminApi.listUsers(),
    select: (res: AxiosResponse) => res.data,
  })

  return (
    <Card title="사용자 관리">
      <Table
        dataSource={data?.items || []}
        loading={isLoading}
        rowKey="id"
        columns={[
          { title: '사용자명', dataIndex: 'username', key: 'username' },
          { title: '이름', dataIndex: 'full_name', key: 'full_name' },
          { title: '이메일', dataIndex: 'email', key: 'email' },
          {
            title: '역할',
            dataIndex: 'role',
            key: 'role',
            render: (role: string) => (
              <Tag color={role === 'admin' ? 'red' : role === 'manager' ? 'orange' : 'blue'}>
                {role}
              </Tag>
            ),
          },
          { title: '부서', dataIndex: 'department', key: 'department' },
          {
            title: '상태',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => (
              <Tag color={active ? 'success' : 'default'}>
                {active ? '활성' : '비활성'}
              </Tag>
            ),
          },
          {
            title: '마지막 로그인',
            dataIndex: 'last_login',
            key: 'last_login',
            render: (date: string) =>
              date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
          },
        ]}
      />
    </Card>
  )
}

function AdminAuditLogs() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'audit-logs'],
    queryFn: () => adminApi.getAuditLogs(),
    select: (res: AxiosResponse) => res.data,
  })

  return (
    <Card title="감사 로그">
      <Table
        dataSource={data?.items || []}
        loading={isLoading}
        rowKey="id"
        columns={[
          {
            title: '시간',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
          },
          { title: '사용자', dataIndex: 'user', key: 'user' },
          {
            title: '작업',
            dataIndex: 'action',
            key: 'action',
            render: (action: string) => <Tag>{action}</Tag>,
          },
          { title: '리소스 유형', dataIndex: 'resource_type', key: 'resource_type' },
          { title: 'IP', dataIndex: 'ip_address', key: 'ip_address' },
        ]}
        pagination={{ pageSize: 20 }}
      />
    </Card>
  )
}

function AdminAnalytics() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'analytics'],
    queryFn: () => adminApi.getSearchAnalytics(7),
    select: (res: AxiosResponse) => res.data,
  })

  if (isLoading) {
    return <Card loading />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Title level={4}>검색 분석 (최근 7일)</Title>

      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic title="총 검색 수" value={data?.total_searches || 0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="평균 응답 시간"
              value={data?.average_latency_ms || 0}
              suffix="ms"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="도움됨 피드백"
              value={data?.feedback?.helpful || 0}
              suffix={`/ ${(data?.feedback?.helpful || 0) + (data?.feedback?.not_helpful || 0)}`}
            />
          </Card>
        </Col>
      </Row>

      <Card title="인기 검색어">
        <Table
          dataSource={data?.top_queries || []}
          rowKey="query"
          pagination={false}
          columns={[
            { title: '검색어', dataIndex: 'query', key: 'query' },
            { title: '횟수', dataIndex: 'count', key: 'count' },
          ]}
        />
      </Card>
    </div>
  )
}

function AdminPage() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { key: '/admin', icon: <DashboardOutlined />, label: '대시보드' },
    { key: '/admin/users', icon: <UserOutlined />, label: '사용자' },
    { key: '/admin/audit', icon: <SettingOutlined />, label: '감사 로그' },
    { key: '/admin/analytics', icon: <SearchOutlined />, label: '검색 분석' },
  ]

  return (
    <div style={{ display: 'flex', gap: 16 }}>
      <Card style={{ width: 200 }} styles={{ body: { padding: 0 } }}>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: 0 }}
        />
      </Card>

      <div style={{ flex: 1 }}>
        <Routes>
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="audit" element={<AdminAuditLogs />} />
          <Route path="analytics" element={<AdminAnalytics />} />
        </Routes>
      </div>
    </div>
  )
}

export default AdminPage
