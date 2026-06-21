"use client";

import { Alert, Button, Card, Statistic, Table, Tabs, Typography } from "antd";
import { useState } from "react";
import { apiClient } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";

const { Paragraph, Title } = Typography;

export default function KnowledgePage() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [results, setResults] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);

  const loadStats = async () => {
    const resp = await apiClient.get<{ code: number; data: Record<string, unknown> }>(
      "/knowledge/stats",
    );
    setStats(resp.data.data);
  };

  const runSearch = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.post<{ code: number; data: { results: Array<Record<string, unknown>> } }>(
        "/knowledge/search",
        { query: "MEB chassis suspension", top_k: 5 },
      );
      setResults(resp.data.data.results);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={3}>知识库</Title>
      <Paragraph type="secondary">
        管理历史项目文档与原子模块知识（Demo：文档检索可用；原子模块目录 Phase 2）。
      </Paragraph>

      <DemoModuleCapability module="knowledge" />

      <Tabs
        defaultActiveKey="docs"
        items={[
          {
            key: "docs",
            label: "文档检索",
            children: (
              <>
                <Card style={{ marginBottom: 16 }}>
                  <Button onClick={loadStats} style={{ marginRight: 8 }}>
                    刷新统计
                  </Button>
                  <Button type="primary" loading={loading} onClick={runSearch}>
                    测试检索
                  </Button>
                  {stats && (
                    <div style={{ marginTop: 16, display: "flex", gap: 32 }}>
                      <Statistic title="文档数" value={Number(stats.total_documents || 0)} />
                      <Statistic title="项目数" value={Number(stats.total_projects || 0)} />
                    </div>
                  )}
                </Card>

                {results.length > 0 && (
                  <Card title="检索结果">
                    <Table
                      rowKey={(_, i) => String(i)}
                      size="small"
                      dataSource={results}
                      pagination={false}
                      columns={[
                        {
                          title: "项目",
                          dataIndex: ["metadata", "project_name"],
                        },
                        {
                          title: "相似度",
                          dataIndex: "similarity_score",
                          render: (v: number) => `${Math.round(v * 100)}%`,
                        },
                        { title: "内容", dataIndex: "content" },
                      ]}
                    />
                  </Card>
                )}
              </>
            ),
          },
          {
            key: "modules",
            label: "原子模块（Demo 占位）",
            children: (
              <Card>
                <Alert
                  type="info"
                  showIcon
                  message="Phase 2：按 technical_module 切块的知识目录"
                  description="Demo 阶段展示占位。后续支持模块浏览、导入与可编辑检索 query。"
                />
                <Table
                  style={{ marginTop: 16 }}
                  rowKey="key"
                  size="small"
                  pagination={false}
                  dataSource={[
                    { key: "Chassis-Suspension-FEA", function: "Chassis", name: "悬架布置与载荷" },
                    { key: "Chassis-Steering-Layout", function: "Chassis", name: "转向系统布置" },
                    { key: "PM-Project-Control", function: "PM", name: "项目计划与控制" },
                  ]}
                  columns={[
                    { title: "模块 Key", dataIndex: "key" },
                    { title: "Function", dataIndex: "function", width: 100 },
                    { title: "名称", dataIndex: "name" },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
