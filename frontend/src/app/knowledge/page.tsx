"use client";

import { Alert, Card, Statistic, Typography } from "antd";

const { Paragraph, Title } = Typography;

export default function KnowledgePage() {
  return (
    <div>
      <Title level={3}>知识库</Title>
      <Paragraph type="secondary">
        管理历史项目文档，支持增量导入与向量检索。
      </Paragraph>
      <Alert
        message="Phase 0 脚手架"
        description="知识库 ingest 与 search API 将在 RAG 模块开发阶段接入。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      <Card>
        <Statistic title="已索引文档" value={0} suffix="份" />
      </Card>
    </div>
  );
}
