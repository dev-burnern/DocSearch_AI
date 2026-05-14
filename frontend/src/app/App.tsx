import { Layout, Space, Tag, Typography } from "antd";

import { ChatWorkspace } from "../features/chat/ChatWorkspace";

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
        <ChatWorkspace />
      </Content>
    </Layout>
  );
}
