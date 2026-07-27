"use client";

import {
  Alert,
  Badge,
  Button,
  Card,
  Drawer,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  InfoCircleOutlined,
  ReloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";
import EngagementInventoryPanel from "@/components/EngagementInventoryPanel";
import EngagementUploadPanel from "@/components/EngagementUploadPanel";
import KbCapacityAlert from "@/components/KbCapacityAlert";
import KnowledgeIndexJobPanel from "@/components/KnowledgeIndexJobPanel";
import { useAuth } from "@/context/AuthContext";
import { useUiProfile } from "@/hooks/useUiProfile";
import {
  getKnowledgePageVisibility,
  knowledgeDocumentsEmptyText,
  knowledgePageIntro,
  knowledgePageTitle,
  knowledgeSearchHint,
} from "@/lib/knowledgePageVisibility";
import { actionAreaErrorFromAxios } from "@/lib/rfqBusyUx";
import { ENGAGEMENT_FUNCTION_OPTIONS } from "@/lib/engagementMetadata";

const { Paragraph, Text, Title } = Typography;

const FUNCTION_OPTIONS = [...ENGAGEMENT_FUNCTION_OPTIONS];
const DOC_TYPE_OPTIONS = [
  { value: "rfq", label: "RFQ" },
  { value: "qa", label: "QA 清单" },
  { value: "quote_manpower", label: "人力报价" },
  { value: "summary", label: "方案 / 摘要" },
];

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
  modified_at?: string | null;
  error?: string;
  engagement_id?: string;
  customer?: string | null;
  year?: number | null;
  functions?: string[];
  metadata_summary?: string | null;
}

interface RAGHitRow {
  content: string;
  similarity_score: number;
  metadata?: {
    project_name?: string;
    source_doc?: string;
    doc_type?: string;
    functions?: string[];
    engagement_id?: string;
    chunk_chapter?: string;
    section_path?: string;
  };
}

interface SearchGroupRow {
  engagement_id?: string | null;
  project_name: string;
  similarity_score: number;
  source_doc?: string | null;
  metadata?: RAGHitRow["metadata"];
  hits: RAGHitRow[];
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
  const { authEnabled, isKbAdmin } = useAuth();
  const { health, showDemoChrome, isFormalDelivery } = useUiProfile();
  const visibility = getKnowledgePageVisibility({
    authEnabled,
    isKbAdmin,
    isFormalDelivery,
  });
  const { canWriteKb } = visibility;
  const writeProtected = health?.data_volume?.write_protected === true;
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [results, setResults] = useState<RAGHitRow[]>([]);
  const [groups, setGroups] = useState<SearchGroupRow[]>([]);
  const [query, setQuery] = useState("MEB 底盘 悬架");
  const [topK, setTopK] = useState(5);
  const [functionFilter, setFunctionFilter] = useState<string[]>([]);
  const [docTypeFilter, setDocTypeFilter] = useState<string[]>([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [docsLoading, setDocsLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchActionError, setSearchActionError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("projects");
  const [insufficientEvidence, setInsufficientEvidence] = useState<boolean | null>(null);
  const [listRefresh, setListRefresh] = useState(0);
  const [indexStartSignal, setIndexStartSignal] = useState(0);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadMetaIncomplete, setUploadMetaIncomplete] = useState(false);
  const [pendingReindexCount, setPendingReindexCount] = useState(0);

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

  const loadPendingReindexCount = useCallback(async () => {
    try {
      const resp = await apiClient.get<{
        code: number;
        data: { engagements: { index_status: string }[] };
      }>("/knowledge/engagements");
      const rows = resp.data.data.engagements ?? [];
      // Only pending = content changed / awaiting「更新检索」.
      // failed（如信息不完整）已由下方任务警告引导「完善信息」，不计入角标，避免误导连点。
      setPendingReindexCount(rows.filter((e) => e.index_status === "pending").length);
    } catch {
      setPendingReindexCount(0);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setListRefresh((n) => n + 1);
    await Promise.all([loadStats(), loadDocuments(), loadPendingReindexCount()]);
  }, [loadDocuments, loadStats, loadPendingReindexCount]);

  const handleIndexCompleted = useCallback(async () => {
    await refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    void loadStats();
    void loadDocuments();
    void loadPendingReindexCount();
  }, [loadStats, loadDocuments, loadPendingReindexCount]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    if (q) {
      setQuery(decodeURIComponent(q));
      setActiveTab("search");
    }
    const tab = params.get("tab");
    if (tab === "docs" || tab === "baselines" || tab === "modules") {
      setActiveTab("projects");
    } else if (tab === "search" || tab === "projects") {
      setActiveTab(tab);
    }
  }, []);

  const runSearch = async () => {
    if (query.trim().length < 2) {
      message.warning("关键词至少 2 个字符");
      return;
    }
    setSearchLoading(true);
    setSearchActionError(null);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: {
          groups?: SearchGroupRow[];
          results: RAGHitRow[];
          insufficient_evidence?: boolean;
        };
      }>(
        "/knowledge/search",
        {
          query: query.trim(),
          top_k: topK,
          function_filter: functionFilter.length ? functionFilter : undefined,
          doc_type_filter: docTypeFilter.length ? docTypeFilter : undefined,
        },
        { silentError: true },
      );
      const nextGroups = resp.data.data.groups ?? [];
      setGroups(nextGroups);
      setResults(resp.data.data.results ?? []);
      setInsufficientEvidence(resp.data.data.insufficient_evidence ?? null);
      if (nextGroups.length === 0 && (resp.data.data.results ?? []).length === 0) {
        message.info("未找到匹配结果，可调整关键词或先更新检索");
      }
    } catch (err) {
      const action = actionAreaErrorFromAxios(err);
      if (action?.kind === "search_busy") {
        setSearchActionError(action.message);
      } else {
        message.error(action?.message || "检索失败");
      }
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div>
      <Space align="center" style={{ marginBottom: 8 }}>
        <Title level={3} style={{ margin: 0 }}>
          {knowledgePageTitle(canWriteKb)}
        </Title>
        <Tag color="blue">平台能力</Tag>
      </Space>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        {knowledgePageIntro(canWriteKb)}
      </Paragraph>

      {stats?.mock_rag && showDemoChrome && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={
            <Space>
              <Tag color="orange">演示数据</Tag>
              <span>当前统计与检索为演示示例；接入真实资料后将显示实际数据。</span>
            </Space>
          }
        />
      )}

      {stats?.mock_rag && isFormalDelivery && visibility.showOpsMockRagAlert && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="生产环境不应启用 Mock RAG，请检查部署配置（MOCK_RAG=false）。"
        />
      )}

      <DemoModuleCapability module="knowledge" />

      {visibility.showCapacityAlert && <KbCapacityAlert volume={health?.data_volume} />}

      <Card size="small" style={{ marginBottom: 16 }} loading={statsLoading}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: 24,
            alignItems: "start",
          }}
        >
          <Statistic
            title={<StatLabel title="历史项目" tip="知识库中的历史项目数量。" />}
            value={stats?.total_projects ?? 0}
            valueStyle={{ fontSize: 22, fontWeight: 600, lineHeight: "32px" }}
          />
          <Statistic
            title={
              <StatLabel title="文档数" tip="项目包中的 RFQ、QA、人力报价等文件数量。" />
            }
            value={stats?.total_documents ?? 0}
            valueStyle={{ fontSize: 22, fontWeight: 600, lineHeight: "32px" }}
          />
          <Statistic
            title={
              <StatLabel
                title="知识条目"
                tip="可供「相似历史项目」检索使用的内容条数。"
              />
            }
            value={stats?.total_chunks ?? 0}
            valueStyle={{ fontSize: 22, fontWeight: 600, lineHeight: "32px" }}
          />
          <Statistic
            title={
              <StatLabel title="最近更新" tip="最近一次把项目资料更新进检索库的时间。" />
            }
            value={
              stats?.last_import_at
                ? new Date(stats.last_import_at).toLocaleString("zh-CN")
                : "尚未更新"
            }
            valueStyle={{ fontSize: 16, fontWeight: 600, lineHeight: "32px" }}
          />
        </div>
      </Card>

      {canWriteKb && (
        <Space wrap style={{ marginBottom: 12 }} size={12}>
          {visibility.showUpload && (
            <Button
              type={pendingReindexCount > 0 ? "default" : "primary"}
              icon={<UploadOutlined />}
              disabled={writeProtected}
              onClick={() => setUploadOpen(true)}
            >
              添加历史项目
            </Button>
          )}
          {visibility.showIndexJob && (
            <Badge count={pendingReindexCount} size="small" offset={[4, 0]}>
              <Button
                disabled={writeProtected}
                type={pendingReindexCount > 0 ? "primary" : "default"}
                onClick={() => setIndexStartSignal((n) => n + 1)}
              >
                更新检索
              </Button>
            </Badge>
          )}
          <Button
            icon={<ReloadOutlined />}
            loading={statsLoading || docsLoading}
            onClick={() => void refreshAll()}
          >
            刷新
          </Button>
          <Tooltip title="添加历史项目：上传资料 → 完善客户/年份/领域 → 更新检索。异常请看列表中的检索可用性。">
            <Text type="secondary" style={{ cursor: "help" }}>
              <InfoCircleOutlined /> 使用说明
            </Text>
          </Tooltip>
          {pendingReindexCount > 0 ? (
            <Text type="warning" style={{ fontSize: 13 }}>
              有 {pendingReindexCount} 个项目资料待写入检索库，请点击「更新检索」
            </Text>
          ) : null}
        </Space>
      )}

      {visibility.showIndexJob && (
        <KnowledgeIndexJobPanel
          onCompleted={handleIndexCompleted}
          writeProtected={writeProtected}
          startSignal={indexStartSignal}
          hideStartButton
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "projects",
            label: "历史项目",
            children: visibility.showEngagementInventory ? (
              <EngagementInventoryPanel
                refreshToken={listRefresh}
                canEdit={visibility.canWriteKb}
                writeProtected={writeProtected}
                documents={documents}
                documentsLoading={docsLoading}
                hideBuiltinRefresh
                onChanged={refreshAll}
                emptyText={knowledgeDocumentsEmptyText({
                  canWriteKb,
                  showDemoChrome,
                })}
              />
            ) : (
              <Alert
                type="info"
                showIcon
                message="当前环境未展示历史项目清单"
                description="正式交付画像下将显示可展开的历史项目表。"
              />
            ),
          },
          {
            key: "search",
            label: "检索",
            children: (
              <Card title="历史资料检索" style={{ marginBottom: 16 }}>
                <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                  {knowledgeSearchHint(canWriteKb)}
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
                    <Tooltip title="最多返回多少个历史项目（按项目聚合）">
                      <Text type="secondary">返回项目数</Text>
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

                {searchActionError && (
                  <Alert
                    type="error"
                    showIcon
                    closable
                    onClose={() => setSearchActionError(null)}
                    style={{ marginBottom: 16 }}
                    message="检索暂时不可用"
                    description={searchActionError}
                    data-testid="knowledge-search-action-error"
                  />
                )}

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
                  rowKey={(row, i) =>
                    String(row.engagement_id || row.project_name || row.source_doc || i)
                  }
                  size="small"
                  loading={searchLoading}
                  dataSource={
                    groups.length
                      ? groups
                      : results.map((hit, i) => ({
                          engagement_id: hit.metadata?.engagement_id,
                          project_name: hit.metadata?.project_name || "—",
                          similarity_score: hit.similarity_score,
                          source_doc: hit.metadata?.source_doc,
                          metadata: hit.metadata,
                          hits: [hit],
                        }))
                  }
                  pagination={false}
                  locale={{ emptyText: "输入关键词后点击检索" }}
                  expandable={{
                    expandedRowRender: (row: SearchGroupRow) => (
                      <Table
                        size="small"
                        pagination={false}
                        rowKey={(_, i) => String(i)}
                        dataSource={row.hits || []}
                        columns={[
                          {
                            title: "章节路径",
                            width: 280,
                            render: (_: unknown, hit: RAGHitRow) =>
                              hit.metadata?.section_path || hit.metadata?.chunk_chapter || "—",
                          },
                          {
                            title: "相似度",
                            dataIndex: "similarity_score",
                            width: 80,
                            render: (v: number) => `${Math.round(v * 100)}%`,
                          },
                          {
                            title: "类型",
                            width: 72,
                            render: (_: unknown, hit: RAGHitRow) => hit.metadata?.doc_type || "—",
                          },
                          {
                            title: "内容片段",
                            dataIndex: "content",
                            ellipsis: true,
                          },
                        ]}
                      />
                    ),
                    rowExpandable: (row: SearchGroupRow) => (row.hits?.length || 0) > 0,
                  }}
                  columns={[
                    {
                      title: "历史项目",
                      width: 220,
                      render: (_: unknown, row: SearchGroupRow) =>
                        row.project_name || row.metadata?.project_name || "—",
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
                      render: (_: unknown, row: SearchGroupRow) =>
                        row.metadata?.doc_type || row.hits?.[0]?.metadata?.doc_type || "—",
                    },
                    {
                      title: "来源文档",
                      width: 200,
                      render: (_: unknown, row: SearchGroupRow) =>
                        row.source_doc || row.metadata?.source_doc || "—",
                    },
                    {
                      title: "工程领域",
                      width: 120,
                      render: (_: unknown, row: SearchGroupRow) =>
                        (row.metadata?.functions || row.hits?.[0]?.metadata?.functions || []).join(
                          "、",
                        ) || "—",
                    },
                    {
                      title: "命中出处",
                      width: 88,
                      render: (_: unknown, row: SearchGroupRow) =>
                        `${row.hits?.length || 0} 条`,
                    },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />

      {visibility.showUpload && (
        <Drawer
          title="添加历史项目"
          open={uploadOpen}
          onClose={() => {
            if (uploadMetaIncomplete) {
              Modal.confirm({
                title: "项目信息尚未完善",
                content:
                  "关闭后可在「历史项目」中继续完善。未填写的项目名、客户、年份无法在 RFQ 相似历史中正确显示，且不能更新检索。",
                okText: "仍要关闭",
                cancelText: "继续填写",
                onOk: () => {
                  setUploadOpen(false);
                  setUploadMetaIncomplete(false);
                },
              });
              return;
            }
            setUploadOpen(false);
          }}
          width={Math.min(560, typeof window !== "undefined" ? window.innerWidth - 24 : 560)}
          destroyOnClose={false}
          styles={{ body: { paddingTop: 12 } }}
        >
          <EngagementUploadPanel
            variant="plain"
            writeProtected={writeProtected}
            onMetadataIncompleteChange={setUploadMetaIncomplete}
            onUploaded={() => {
              void refreshAll();
            }}
            onRequestIndex={() => {
              setUploadOpen(false);
              setUploadMetaIncomplete(false);
              setIndexStartSignal((n) => n + 1);
            }}
          />
        </Drawer>
      )}
    </div>
  );
}
