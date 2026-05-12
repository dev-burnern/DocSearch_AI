import { Card, Col, Layout, Row, Space, Tag, Typography } from "antd";

const { Content, Header } = Layout;
const { Paragraph, Title } = Typography;

const panels = [
  {
    title: "Upload",
    description: "Document ingestion workflow will land here.",
  },
  {
    title: "Search",
    description: "Retrieval and ranking results surface will live here.",
  },
  {
    title: "Chat",
    description: "Cited RAG responses will be shown here.",
  },
];

export default function App() {
  return (
    <Layout style={{ minHeight: "100vh", background: "#f5f7fb" }}>
      <Header
        style={{
          background: "#ffffff",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
        }}
      >
        <Space direction="vertical" size={0}>
          <Title level={4} style={{ margin: 0 }}>
            DocSearch AI V2
          </Title>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            On-premise document search and RAG shell
          </Paragraph>
        </Space>
      </Header>
      <Content style={{ padding: 32 }}>
        <Space direction="vertical" size={24} style={{ width: "100%" }}>
          <Space wrap>
            <Tag color="blue">React</Tag>
            <Tag color="geekblue">TypeScript</Tag>
            <Tag color="purple">Vite</Tag>
            <Tag color="cyan">Ant Design</Tag>
          </Space>
          <Row gutter={[16, 16]}>
            {panels.map((panel) => (
              <Col key={panel.title} xs={24} md={8}>
                <Card title={panel.title} bordered={false}>
                  <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    {panel.description}
                  </Paragraph>
                </Card>
              </Col>
            ))}
          </Row>
        </Space>
      </Content>
    </Layout>
  );
}
