"use client";

import {
  Alert,
  Button,
  Card,
  Input,
  InputNumber,
  Progress,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";

const { Paragraph, Text, Title } = Typography;

interface KnowledgeStats {
  total_documents?: number;
  total_chunks?: number;
  total_projects?: number;
  last_import_at?: string | null;
  function_coverage?: Record<string, number>;
  mock_rag?: boolean;
}

interface RAGHitRow {
  content: string;
  similarity_score: number;
  metadata?: {
    project_name?: string;
    source_doc?: string;
    doc_type?: string;
    functions?: string[];
  };
}

function coverageColor(rate: number): string {
  if (rate >= 0.7) return "#52c41a";
  if (rate >= 0.4) return "#faad14";
  return "#ff4d4f";
}

function StatLabel({ title, tip }: { title: string; tip: string }) {
  return (
    <Tooltip title={tip}>
      <Space size={4}>
        <span>{title}</span>
        <InfoCircleOutlined style={{ color: "#999", fontSize: 12 }} />
      </Space>
    </Tooltip>
  );
}

export default function KnowledgePage() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [results, setResults] = useState<RAGHitRow[]>([]);
  const [query, setQuery] = useState("MEB 底盘 悬架");
  const [topK, setTopK] = useState(5);
  const [statsLoading, setStatsLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const resp = await apiClient.get<{ code: number; data: KnowledgeStats }>("/knowledge/stats");
      setStats(resp.data.data);
    } catch {
      message.error("加载统计失败");
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const runSearch = async () => {
    if (query.trim().length < 2) {
      message.warning("关键词至少 2 个字符");
      return;
    }
    setSearchLoading(true);
    try {
      const resp = await apiClient.post<{ code: number; data: { results: RAGHitRow[] } }>(
        "/knowledge/search",
        { query: query.trim(), top_k: topK },
      );
      setResults(resp.data.data.results);
      if (resp.data.data.results.length === 0) {
        message.info("未找到匹配结果，可调整关键词或先更新知识库索引");
      }
    } catch {
      message.error("检索失败");
    } finally {
      setSearchLoading(false);
    }
  };

  const runImport = async () => {
    setImportLoading(true);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: { new_documents: number; new_chunks: number; skipped: number };
      }>("/knowledge/import");
      const { new_documents, new_chunks, skipped } = resp.data.data;
      message.success(
        `索引更新完成：新增 ${new_documents} 篇文档，${new_chunks} 个可检索片段，跳过 ${skipped} 篇`,
      );
      await loadStats();
    } catch {
      message.error("索引更新失败");
    } finally {
      setImportLoading(false);
    }
  };

  const coverageEntries = Object.entries(stats?.function_coverage || {}).sort(
    (a, b) => b[1] - a[1],
  );

  return (
    <div>
      <Title level={3}>历史资料库</Title>
      <Paragraph type="secondary">
        管理历史项目文档，供 RFQ 分析中的历史对标检索使用。报价工程师日常在「RFQ 分析」页查看对标结果即可，无需每日进入本页。
      </Paragraph>

      {stats?.mock_rag && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={
            <Space>
              <Tag color="orange">演示数据</Tag>
              <span>当前统计与检索结果为演示环境示例；接入贵司历史资料后将显示真实数据。</span>
            </Space>
          }
        />
      )}

      <DemoModuleCapability module="knowledge" />

      <Tabs
        defaultActiveKey="docs"
        items={[
          {
            key: "docs",
            label: "历史项目资料",
            children: (
              <>
                <Card title="资料概览" style={{ marginBottom: 16 }} loading={statsLoading}>
                  <Space wrap style={{ marginBottom: 16 }}>
                    <Button onClick={() => void loadStats()} loading={statsLoading}>
                      刷新统计
                    </Button>
                    <Button type="primary" loading={importLoading} onClick={() => void runImport()}>
                      更新知识库索引
                    </Button>
                    <Text type="secondary">
                      先将文件放入服务器目录{" "}
                      <Text code>knowledge_base/&lt;项目名&gt;/</Text>，再点击「更新知识库索引」
                    </Text>
                  </Space>

                  {stats && (
                    <>
                      <div style={{ display: "flex", gap: 32, flexWrap: "wrap", marginBottom: 16 }}>
                        <Statistic
                          title={
                            <StatLabel
                              title="历史文档数"
                              tip="已纳入知识库的项目文档数量（如 RFQ、方案、报价等）"
                            />
                          }
                          value={stats.total_documents ?? 0}
                        />
                        <Statistic
                          title={
                            <StatLabel
                              title="可检索片段数"
                              tip="文档切分后的检索单元；RFQ 对标时匹配的是这些片段，而非整份文件"
                            />
                          }
                          value={stats.total_chunks ?? 0}
                        />
                        <Statistic
                          title={
                            <StatLabel title="历史项目数" tip="知识库中独立项目文件夹的数量" />
                          }
                          value={stats.total_projects ?? 0}
                        />
                        {stats.last_import_at && (
                          <Statistic
                            title="最近索引更新"
                            value={new Date(stats.last_import_at).toLocaleString("zh-CN")}
                          />
                        )}
                      </div>

                      {coverageEntries.length > 0 && (
                        <div>
                          <Text strong>
                            <StatLabel
                              title="工程领域覆盖"
                              tip="各职能模块（如 PM、Chassis、BIW）在历史资料中的丰富程度；覆盖偏低时，RFQ 对标可能缺少参考"
                            />
                          </Text>
                          <Paragraph type="secondary" style={{ marginTop: 4, marginBottom: 12 }}>
                            覆盖偏低的领域，建议在 RFQ 对标时重点人工补充依据，或优先补充该类历史项目资料。
                          </Paragraph>
                          <div style={{ maxWidth: 480 }}>
                            {coverageEntries.map(([fn, rate]) => (
                              <div key={fn} style={{ marginBottom: 8 }}>
                                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                                  <Space size={8}>
                                    <Text>{fn}</Text>
                                    {rate < 0.4 && (
                                      <Tag color="orange" style={{ margin: 0 }}>
                                        建议补充资料
                                      </Tag>
                                    )}
                                  </Space>
                                  <Text type="secondary">{Math.round(rate * 100)}%</Text>
                                </Space>
                                <Progress
                                  percent={Math.round(rate * 100)}
                                  showInfo={false}
                                  strokeColor={coverageColor(rate)}
                                  size="small"
                                />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </Card>

                <Card title="历史资料检索" style={{ marginBottom: 16 }}>
                  <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                    RFQ 分析页中的「相似历史项目」由相同检索逻辑产生，可在此验证关键词能否命中预期资料。
                  </Paragraph>
                  <Space wrap style={{ marginBottom: 16 }}>
                    <Input
                      style={{ width: 360 }}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="输入关键词，如 MEB 底盘 悬架"
                      onPressEnter={() => void runSearch()}
                    />
                    <Space>
                      <Tooltip title="最多返回多少条相似结果">
                        <Text type="secondary">返回条数</Text>
                      </Tooltip>
                      <InputNumber min={1} max={20} value={topK} onChange={(v) => setTopK(v ?? 5)} />
                    </Space>
                    <Button type="primary" loading={searchLoading} onClick={() => void runSearch()}>
                      检索
                    </Button>
                  </Space>

                  <Table
                    rowKey={(_, i) => String(i)}
                    size="small"
                    loading={searchLoading}
                    dataSource={results}
                    pagination={false}
                    locale={{ emptyText: "输入关键词后点击检索" }}
                    columns={[
                      {
                        title: "历史项目",
                        width: 220,
                        render: (_, row) => row.metadata?.project_name || "—",
                      },
                      {
                        title: "相似度",
                        dataIndex: "similarity_score",
                        width: 80,
                        render: (v: number) => `${Math.round(v * 100)}%`,
                      },
                      {
                        title: "来源文档",
                        width: 200,
                        render: (_, row) => row.metadata?.source_doc || "—",
                      },
                      {
                        title: "工程领域",
                        width: 120,
                        render: (_, row) => (row.metadata?.functions || []).join("、") || "—",
                      },
                      {
                        title: "内容片段",
                        dataIndex: "content",
                        ellipsis: true,
                      },
                    ]}
                  />
                </Card>
              </>
            ),
          },
          {
            key: "modules",
            label: "方案模块目录（即将推出）",
            children: (
              <Card>
                <Alert
                  type="info"
                  showIcon
                  message="正式版功能预览"
                  description="将支持按工程领域浏览历史方案的原子模块。Demo 阶段仅展示占位说明，下列示例数据不代表贵司真实资料。"
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
                    { title: "模块标识", dataIndex: "key" },
                    { title: "工程领域", dataIndex: "function", width: 100 },
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
