"use client";

import {
  Alert,
  Button,
  Card,
  Input,
  InputNumber,
  Progress,
  Select,
  Space,
  Statistic,
  Steps,
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
import EngagementInventoryPanel from "@/components/EngagementInventoryPanel";
import EngagementUploadPanel from "@/components/EngagementUploadPanel";
import KbCapacityAlert from "@/components/KbCapacityAlert";
import KnowledgeImportHistoryPanel from "@/components/KnowledgeImportHistoryPanel";
import KnowledgeIndexJobPanel from "@/components/KnowledgeIndexJobPanel";
import ManpowerBaselinesPanel from "@/components/ManpowerBaselinesPanel";
import PlatformKnowledgeExplainer from "@/components/PlatformKnowledgeExplainer";
import { useAuth } from "@/context/AuthContext";
import { useUiProfile } from "@/hooks/useUiProfile";

const { Paragraph, Text, Title } = Typography;

const FUNCTION_OPTIONS = ["PM", "Chassis", "BIW", "CAE", "EE", "Interior", "GI", "PS", "Test validation"];
const DOC_TYPE_OPTIONS = [
  { value: "rfq", label: "RFQ" },
  { value: "qa", label: "QA 清单" },
  { value: "quote_manpower", label: "人力报价" },
  { value: "summary", label: "方案 / 摘要" },
];

const DOC_TYPE_QUOTING_HINT_DEMO: Record<string, string> = {
  rfq: "RFQ 分析 · 对标参考",
  summary: "RFQ 分析 · 方案摘要",
  qa: "QA 清单 · Phase 2",
  quote_manpower: "人力报价 · Phase 2",
};

const DOC_TYPE_QUOTING_HINT_R1: Record<string, string> = {
  rfq: "RFQ 分析 · 对标参考",
  summary: "RFQ 分析 · 方案摘要",
  qa: "RFQ 分析 · Q_A 检索参考",
  quote_manpower: "人天基线 · 规则解析",
};

interface KnowledgeStats {
  total_documents?: number;
  total_chunks?: number;
  total_projects?: number;
  last_import_at?: string | null;
  function_coverage?: Record<string, number>;
  mock_rag?: boolean;
}

interface KnowledgeDocument {
  path: string;
  project_name: string;
  doc_type: string;
  status: string;
  file_size_bytes?: number;
  error?: string;
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

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  indexed: { color: "green", label: "已索引" },
  pending: { color: "default", label: "待索引" },
  failed: { color: "red", label: "失败" },
};

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

function formatBytes(n?: number): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function KnowledgePage() {
  const { authEnabled, isKbAdmin } = useAuth();
  const { health, showDemoChrome, isFormalDelivery } = useUiProfile();
  const docTypeQuotingHint = showDemoChrome ? DOC_TYPE_QUOTING_HINT_DEMO : DOC_TYPE_QUOTING_HINT_R1;
  const canWriteKb = !authEnabled || isKbAdmin;
  const writeProtected = health?.data_volume?.write_protected === true;
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [results, setResults] = useState<RAGHitRow[]>([]);
  const [query, setQuery] = useState("MEB 底盘 悬架");
  const [topK, setTopK] = useState(5);
  const [functionFilter, setFunctionFilter] = useState<string[]>([]);
  const [docTypeFilter, setDocTypeFilter] = useState<string[]>([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [docsLoading, setDocsLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [activeTab, setActiveTab] = useState("docs");
  const [baselinesEngagementId, setBaselinesEngagementId] = useState<string | null>(null);
  const [insufficientEvidence, setInsufficientEvidence] = useState<boolean | null>(null);
  const [importHistoryRefresh, setImportHistoryRefresh] = useState(0);

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

  const loadDocuments = useCallback(async () => {
    setDocsLoading(true);
    try {
      const resp = await apiClient.get<{ code: number; data: { documents: KnowledgeDocument[] } }>(
        "/knowledge/documents",
      );
      setDocuments(resp.data.data.documents);
    } catch {
      message.error("加载文档列表失败");
    } finally {
      setDocsLoading(false);
    }
  }, []);

  const handleIndexCompleted = useCallback(async () => {
    setWizardStep(2);
    setImportHistoryRefresh((value) => value + 1);
    await Promise.all([loadStats(), loadDocuments()]);
  }, [loadDocuments, loadStats]);

  useEffect(() => {
    void loadStats();
    void loadDocuments();
  }, [loadStats, loadDocuments]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    if (q) {
      setQuery(decodeURIComponent(q));
    }
    const tab = params.get("tab");
    if (tab) {
      setActiveTab(tab);
    }
    const engagementId = params.get("engagement_id");
    if (engagementId) {
      setBaselinesEngagementId(engagementId);
    }
  }, []);

  useEffect(() => {
    if (stats && stats.total_chunks && stats.total_chunks > 0) {
      setWizardStep(2);
    }
  }, [stats]);

  const runSearch = async () => {
    if (query.trim().length < 2) {
      message.warning("关键词至少 2 个字符");
      return;
    }
    setSearchLoading(true);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: { results: RAGHitRow[]; insufficient_evidence?: boolean };
      }>(
        "/knowledge/search",
        {
          query: query.trim(),
          top_k: topK,
          function_filter: functionFilter.length ? functionFilter : undefined,
          doc_type_filter: docTypeFilter.length ? docTypeFilter : undefined,
        },
      );
      setResults(resp.data.data.results);
      setInsufficientEvidence(resp.data.data.insufficient_evidence ?? null);
      setWizardStep(3);
      if (resp.data.data.results.length === 0) {
        message.info("未找到匹配结果，可调整关键词或先更新知识库索引");
      }
    } catch {
      message.error("检索失败");
    } finally {
      setSearchLoading(false);
    }
  };

  const coverageEntries = Object.entries(stats?.function_coverage || {}).sort(
    (a, b) => b[1] - a[1],
  );

  const indexedCount = documents.filter((d) => d.status === "indexed").length;

  return (
    <div>
      <Space align="center" style={{ marginBottom: 8 }}>
        <Title level={3} style={{ margin: 0 }}>
          知识库
        </Title>
        <Tag color="blue">平台能力</Tag>
      </Space>
      <Paragraph type="secondary">
        历史项目 RFQ、方案、报价等工程资料 · 平台共享检索底座。日常在「RFQ
        分析」查看对标结果；本页可检索与查看统计
        {authEnabled && isKbAdmin ? "，并完成入库与索引。" : "。"}
      </Paragraph>

      <PlatformKnowledgeExplainer />

      {stats?.mock_rag && showDemoChrome && (
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

      {stats?.mock_rag && isFormalDelivery && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="生产环境不应启用 Mock RAG，请检查部署配置（MOCK_RAG=false）。"
        />
      )}

      <DemoModuleCapability module="knowledge" />

      <Card title="入库与验证向导" style={{ marginBottom: 16 }} size="small">
        <Steps
          size="small"
          current={wizardStep}
          items={[
            {
              title: "准备项目资料",
              description: "目录落盘或 Web 上传",
            },
            {
              title: "更新索引",
              description: "扫描并写入向量库",
            },
            {
              title: "查看清单",
              description: `${indexedCount}/${documents.length} 已索引`,
            },
            {
              title: "检索验证",
              description: "确认能命中预期资料",
            },
          ]}
        />
        <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 8 }}>
          <Text strong>R1 入库方式：</Text>
          <Text strong>（A）</Text> IT 将项目包放入服务器{" "}
          <Text code>knowledge_base/&lt;项目名&gt;/</Text>
          （100+ 推荐）→ 点击「更新知识库索引」；
          <Text strong>（B）</Text> 本页「上传项目包」— 单套 ZIP/多文件，或一次最多{" "}
          <Text strong>5 套</Text> → 查看缺件提示 → 更新索引。
        </Paragraph>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          资料不完整（缺 Q&A 或报价）仍可入库，系统会提示哪些自动化环节不可用。运营级拖拽整目录上传不含于当前里程碑。
        </Paragraph>
      </Card>

      {canWriteKb && <KbCapacityAlert volume={health?.data_volume} />}

      {canWriteKb && (
        <EngagementUploadPanel
          writeProtected={writeProtected}
          onUploaded={() => {
            setWizardStep(1);
            void loadDocuments();
          }}
        />
      )}

      {canWriteKb && (
        <KnowledgeIndexJobPanel
          onCompleted={handleIndexCompleted}
          writeProtected={writeProtected}
        />
      )}

      {canWriteKb && isFormalDelivery && (
        <Card title="导入审计" style={{ marginBottom: 16 }}>
          <KnowledgeImportHistoryPanel refreshToken={importHistoryRefresh} />
        </Card>
      )}

      {canWriteKb && isFormalDelivery && (
        <EngagementInventoryPanel refreshToken={importHistoryRefresh} />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
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
                    <Button onClick={() => void loadDocuments()} loading={docsLoading}>
                      刷新文档清单
                    </Button>
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

                <Card title="文档清单" style={{ marginBottom: 16 }}>
                  <Table
                    rowKey="path"
                    size="small"
                    loading={docsLoading}
                    dataSource={documents}
                    pagination={{ pageSize: 8, hideOnSinglePage: true }}
                    locale={{
                      emptyText: showDemoChrome
                        ? "暂无文档；可将项目包放入 knowledge_base/<项目名>/ 或本页「上传项目包」"
                        : "暂无文档；请通过 IT 目录入库或本页「上传项目包」添加 Engagement",
                    }}
                    columns={[
                      { title: "路径", dataIndex: "path", ellipsis: true },
                      { title: "项目", dataIndex: "project_name", width: 140 },
                      {
                        title: "类型",
                        dataIndex: "doc_type",
                        width: 100,
                        render: (v: string, row: KnowledgeDocument) => {
                          const label = DOC_TYPE_OPTIONS.find((o) => o.value === v)?.label || v;
                          const hint =
                            row.status === "indexed" ? docTypeQuotingHint[v] : undefined;
                          return hint ? (
                            <Tooltip title={`报价环节参考：${hint}`}>
                              <span>{label}</span>
                            </Tooltip>
                          ) : (
                            label
                          );
                        },
                      },
                      {
                        title: "大小",
                        dataIndex: "file_size_bytes",
                        width: 88,
                        render: (v: number) => formatBytes(v),
                      },
                      {
                        title: "状态",
                        dataIndex: "status",
                        width: 100,
                        render: (v: string, row: KnowledgeDocument) => {
                          const cfg = STATUS_TAG[v] || { color: "default", label: v };
                          const tag = <Tag color={cfg.color}>{cfg.label}</Tag>;
                          if (
                            showDemoChrome &&
                            v === "failed" &&
                            (row.doc_type === "quote_manpower" || row.path.endsWith(".xlsx"))
                          ) {
                            return (
                              <Tooltip title="Demo 暂不支持 Excel 入库；Phase 2 将通过项目包 manifest 关联 QA / 报价等文件">
                                {tag}
                              </Tooltip>
                            );
                          }
                          return tag;
                        },
                      },
                      {
                        title: "说明",
                        dataIndex: "error",
                        ellipsis: true,
                        render: (v: string) => v || "—",
                      },
                    ]}
                  />
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
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="工程领域筛选"
                      style={{ minWidth: 160 }}
                      value={functionFilter}
                      onChange={setFunctionFilter}
                      options={FUNCTION_OPTIONS.map((f) => ({ value: f, label: f }))}
                    />
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="文档类型"
                      style={{ minWidth: 140 }}
                      value={docTypeFilter}
                      onChange={setDocTypeFilter}
                      options={DOC_TYPE_OPTIONS}
                    />
                    <Button type="primary" loading={searchLoading} onClick={() => void runSearch()}>
                      检索
                    </Button>
                  </Space>

                  {insufficientEvidence === true && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 16 }}
                      message="检索依据不足"
                      description="最高相似度低于阈值，RFQ 对标时系统将提示人工补充历史资料或核对结论。"
                    />
                  )}

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
                        title: "类型",
                        width: 88,
                        render: (_, row) => row.metadata?.doc_type || "—",
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
            key: "baselines",
            label: "人天基线",
            children: <ManpowerBaselinesPanel engagementId={baselinesEngagementId} />,
          },
          ...(showDemoChrome
            ? [
                {
                  key: "modules",
                  label: "原子模块（Phase 2）",
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
              ]
            : []),
        ]}
      />
    </div>
  );
}
