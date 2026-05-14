import { Layout, Space, Tabs, Tag, Typography } from "antd";

import { ChatWorkspace } from "../features/chat/ChatWorkspace";
import { AuditLogWorkspace } from "../features/audit/AuditLogWorkspace";

const { Content, Header } = Layout;
const { Paragraph, Title } = Typography;

export default function App() {
  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Space direction="vertical" size={2}>
          <Title level={3} className="app-title">
            DocSearch AI
          </Title>
          <Paragraph className="app-subtitle">
            온프레미스 RAG 문서 질의응답
          </Paragraph>
        </Space>
        <Space wrap size={8} className="app-tags">
          <Tag color="blue">React</Tag>
          <Tag color="green">FastAPI</Tag>
          <Tag color="purple">vLLM</Tag>
          <Tag color="cyan">Qdrant</Tag>
        </Space>
      </Header>
      <Content className="app-content">
        <Tabs
          defaultActiveKey="chat"
          items={[
            {
              key: "chat",
              label: "채팅",
              children: <ChatWorkspace />,
            },
            {
              key: "audit",
              label: "감사 로그",
              children: <AuditLogWorkspace />,
            },
          ]}
        />
      </Content>
    </Layout>
  );
}
