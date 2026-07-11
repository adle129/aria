"use client";

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import { BugOutlined } from "@ant-design/icons";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient, fetchHealth } from "@/api/client";

const { Paragraph, Text, Title } = Typography;

const UI_PROFILE = process.env.NEXT_PUBLIC_ARIA_UI_PROFILE || "experience";

function isDebugUiAllowed(health: { aria_ui_profile?: string; kb_debug_enabled?: boolean } | null): boolean {
  const profile = health?.aria_ui_profile || UI_PROFILE;
  return profile === "dev" && health?.kb_debug_enabled === true;
}

interface DebugStatus {
  kb_debug_enabled: boolean;
  mock_rag: boolean;
  corpus_path: string;
  corpus_exists: boolean;
  indexed_chunks: number;
  last_index_at?: string | null;
  embedding_model: string;
  ollama_reachable: boolean;
  embedding_model_ready: boolean;
  ollama_error?: string | null;
}

interface CorpusFile {
  filename: string;
  file_role: string;
  size_bytes: number;
  indexable: boolean;
  archive_only?: boolean;
}

const FILE_ROLE_LABEL: Record<string, string> = {
  rfq: "RFQ",
  qa: "Q_A Excel",
  quote_manpower: "报价 Excel",
  proposal_archive: "方案归档",
  unknown: "未知",
};

const FILE_ROLE_COLOR: Record<string, string> = {
  rfq: "blue",
  qa: "green",
  quote_manpower: "orange",
  proposal_archive: "default",
  unknown: "red",
};

type SearchDocType = "rfq" | "qa" | "all";

const SEARCH_DOC_TYPE_OPTIONS: { value: SearchDocType; label: string }[] = [
  { value: "rfq", label: "RFQ（章节切块）" },
  { value: "qa", label: "Q_A（按行）" },
  { value: "all", label: "全部（混搜 · 高级）" },
];

const FILE_ROLE_TO_SEARCH_DOC: Partial<Record<string, SearchDocType>> = {
  rfq: "rfq",
  qa: "qa",
};

interface ChunkRow {
  chunk_id: string;
  chunk_type?: string;
  chunk_chapter?: string;
  char_count?: number;
  preview?: string;
  metadata?: Record<string, string>;
}

interface SearchHit {
  chunk_id?: string;
  content: string;
  similarity_score: number;
  metadata?: Record<string, unknown>;
}

export default function KnowledgeDebugPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [status, setStatus] = useState<DebugStatus | null>(null);
  const [chunks, setChunks] = useState<ChunkRow[]>([]);
  const [chunkTotal, setChunkTotal] = useState(0);
  const [selectedChunk, setSelectedChunk] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState("物理对标 benchmark");
  const [topK, setTopK] = useState(5);
  const [searchDocType, setSearchDocType] = useState<SearchDocType>("rfq");
  const [areaFilter, setAreaFilter] = useState<string[]>([]);
  const [qaAreas, setQaAreas] = useState<string[]>([]);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [evalSummary, setEvalSummary] = useState<{ total: number; passed: number; pass_rate: number } | null>(
    null,
  );
  const [loading, setLoading] = useState<string | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [previewErrors, setPreviewErrors] = useState<Array<{ file: string; error: string }>>([]);
  const [corpusFiles, setCorpusFiles] = useState<CorpusFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [previewMeta, setPreviewMeta] = useState<{
    file_role?: string;
    browse_mode?: string;
    quote_baselines?: Record<string, unknown>;
    archive_only?: Array<Record<string, unknown>>;
  } | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        if (!isDebugUiAllowed(h)) {
          setAllowed(false);
          router.replace("/knowledge");
          return;
        }
        setAllowed(true);
      })
      .catch(() => {
        setAllowed(false);
        router.replace("/knowledge");
      });
  }, [router]);

  const loadStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const resp = await apiClient.get<{ code: number; data: DebugStatus }>("/knowledge/debug/status");
      setStatus(resp.data.data);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  const loadCorpusFiles = useCallback(async () => {
    const resp = await apiClient.get<{ code: number; data: { items: CorpusFile[] } }>("/knowledge/debug/files");
    const items = resp.data.data.items;
    setCorpusFiles(items);
    setSelectedFile((prev) => {
      if (prev && items.some((f) => f.filename === prev)) return prev;
      const qa = items.find((f) => f.file_role === "qa");
      return qa?.filename ?? items[0]?.filename ?? null;
    });
  }, []);

  const loadChunks = useCallback(async () => {
    const probe = await apiClient.get<{
      code: number;
      data: { total: number };
    }>("/knowledge/debug/chunks", { params: { limit: 1, offset: 0 } });
    const total = probe.data.data.total ?? 0;
    const limit = Math.min(Math.max(total, 1), 2000);
    const resp = await apiClient.get<{
      code: number;
      data: {
        items: ChunkRow[];
        total: number;
        target_file?: string | null;
        file_role?: string;
        browse_mode?: string;
        quote_baselines?: Record<string, unknown>;
        archive_only?: Array<Record<string, unknown>>;
        qa_areas?: string[];
      };
    }>("/knowledge/debug/chunks", { params: { limit, offset: 0 } });
    setChunks(resp.data.data.items);
    setChunkTotal(resp.data.data.total);
    setQaAreas(resp.data.data.qa_areas ?? []);
    setPreviewMeta({
      file_role: resp.data.data.file_role,
      browse_mode: resp.data.data.browse_mode,
      quote_baselines: resp.data.data.quote_baselines,
      archive_only: resp.data.data.archive_only,
    });
    if (resp.data.data.target_file) {
      setSelectedFile(resp.data.data.target_file);
    }
  }, []);

  useEffect(() => {
    if (!allowed) return;
    void loadStatus();
    void loadCorpusFiles();
    void loadChunks();
  }, [allowed, loadStatus, loadCorpusFiles, loadChunks]);

  const chunkTabLabel =
    previewMeta?.file_role === "quote_manpower" || previewMeta?.browse_mode === "baseline_rows"
      ? `Baselines 浏览器 (${chunkTotal})`
      : `切块浏览器 (${chunkTotal})`;

  const isBaselineBrowse =
    previewMeta?.file_role === "quote_manpower" || previewMeta?.browse_mode === "baseline_rows";

  const selectedFileMeta = corpusFiles.find((f) => f.filename === selectedFile);
  const selectedFileRole = selectedFileMeta?.file_role;
  const searchBlockedForQuote = selectedFileRole === "quote_manpower";

  useEffect(() => {
    if (!selectedFile || !selectedFileRole) return;
    const mapped = FILE_ROLE_TO_SEARCH_DOC[selectedFileRole];
    if (mapped) {
      setSearchDocType(mapped);
    }
  }, [selectedFile, selectedFileRole]);

  const handleSearchDocTypeChange = (value: SearchDocType) => {
    setSearchDocType(value);
    if (value !== "qa") {
      setAreaFilter([]);
    }
  };

  const runPreviewFile = async () => {
    if (!selectedFile) {
      message.warning("请先选择语料文件");
      return;
    }
    const fileMeta = corpusFiles.find((f) => f.filename === selectedFile);
    setLoading("preview");
    const hide = message.loading(`正在解析 ${selectedFile}（单文件，约 10–60 秒）...`, 0);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: {
          errors?: Array<{ file: string; error: string }>;
          summary?: Record<string, unknown>;
          file_role?: string;
          quote_baselines?: Record<string, unknown>;
          archive_only?: Array<Record<string, unknown>>;
          indexable_chunks?: unknown[];
        };
      }>("/knowledge/debug/preview-file", { filename: selectedFile }, { timeout: 300000 });
      const data = resp.data.data;
      setPreviewErrors(data.errors ?? []);
      setPreviewMeta({
        file_role: data.file_role,
        browse_mode: undefined,
        quote_baselines: data.quote_baselines,
        archive_only: data.archive_only,
      });
      const chunkCount = Array.isArray(data.indexable_chunks) ? data.indexable_chunks.length : 0;
      if (fileMeta?.indexable) {
        message.success(`预览完成：${chunkCount} 个 chunk`);
      } else if (data.file_role === "quote_manpower") {
        message.success("报价 Excel baselines 已解析（不向量化，见概览详情）");
      } else if (data.file_role === "proposal_archive") {
        message.info("方案文件仅归档，R1 不参与向量检索");
      } else {
        message.warning("该文件无可索引 chunk，见下方告警");
      }
      await loadStatus();
      await loadChunks();
      setActiveTab(
        data.file_role === "quote_manpower"
          ? "chunks"
          : chunkCount === 0
            ? "overview"
            : "chunks",
      );
    } catch {
      message.error("预览失败（检查语料路径或文件格式）");
    } finally {
      hide();
      setLoading(null);
    }
  };

  const runIndex = async () => {
    if (!selectedFile) {
      message.warning("请先选择并预览文件");
      return;
    }
    setLoading("index");
    try {
      const resp = await apiClient.post<{ code: number; data: { indexed_chunks: number } }>(
        "/knowledge/debug/index",
        { filename: selectedFile, clear: true },
        { timeout: 600000 },
      );
      message.success(`已索引 ${resp.data.data.indexed_chunks} 个 chunk（${selectedFile}）`);
      await loadStatus();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "索引失败（需 MOCK_RAG=false 且 nomic-embed-text 就绪）";
      message.error(detail);
    } finally {
      setLoading(null);
    }
  };

  const runSearch = async () => {
    if (searchBlockedForQuote) {
      message.info("报价 Excel 不参与向量检索，请使用「Baselines 浏览器」核对岗位行");
      setActiveTab("chunks");
      return;
    }
    if (query.trim().length < 2) {
      message.warning("关键词至少 2 个字符");
      return;
    }
    setLoading("search");
    try {
      const resp = await apiClient.post<{ code: number; data: { results: SearchHit[] } }>(
        "/knowledge/debug/search",
        {
          query: query.trim(),
          top_k: topK,
          ...(searchDocType !== "all" ? { doc_type_filter: [searchDocType] } : {}),
          ...(searchDocType === "qa" && areaFilter.length > 0 ? { function_filter: areaFilter } : {}),
        },
      );
      setHits(resp.data.data.results);
      if (resp.data.data.results.length === 0) {
        const typeHint =
          searchDocType === "rfq"
            ? "RFQ"
            : searchDocType === "qa"
              ? "Q_A"
              : "全库";
        message.info(
          areaFilter.length > 0
            ? `无 ${typeHint} 结果 — 请检查 Area 过滤、是否已索引 RFQ/Q_A，或换更完整的关键词`
            : `无 ${typeHint} 结果 — 请先对 RFQ 或 Q_A 建立向量索引`,
        );
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "检索失败";
      message.error(detail);
    } finally {
      setLoading(null);
    }
  };

  const openChunk = async (chunkId: string) => {
    try {
      const resp = await apiClient.get<{ code: number; data: Record<string, unknown> }>(
        `/knowledge/debug/chunks/${chunkId}`,
      );
      setSelectedChunk(resp.data.data);
    } catch {
      message.error("加载 chunk 失败");
    }
  };

  const submitFeedback = async (chunkId: string, feedbackType: string) => {
    try {
      await apiClient.post("/knowledge/debug/feedback", {
        feedback_type: feedbackType,
        chunk_id: chunkId,
        source_context: "chunk_inspector",
      });
      message.success(feedbackType === "chunk_ok" ? "已标记 golden" : "反馈已记录");
    } catch {
      message.error("反馈提交失败");
    }
  };

  const runEval = async () => {
    setLoading("eval");
    try {
      const queries = [
        { query: "物理对标 benchmark", expected_doc_types: ["qa"], expected_area: "Packaging" },
        { query: "法规 regulation", expected_doc_types: ["qa"], expected_area: "Packaging" },
        { query: "通用公差 mounting", expected_doc_types: ["qa"], expected_area: "GD&T" },
        { query: "项目总体要求 整车工程", expected_doc_types: ["rfq"], min_score: 0.2 },
        { query: "输入条件 样车", expected_doc_types: ["rfq"], min_score: 0.2 },
      ];
      const resp = await apiClient.post<{
        code: number;
        data: { total: number; passed: number; pass_rate: number };
      }>("/knowledge/debug/eval/run", { queries, top_k: 3 });
      setEvalSummary(resp.data.data);
      message.info(`评测 ${resp.data.data.passed}/${resp.data.data.total} 通过`);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "评测失败";
      message.error(detail);
    } finally {
      setLoading(null);
    }
  };

  if (allowed === null) {
    return <Card loading />;
  }
  if (!allowed) {
    return null;
  }

  return (
    <div>
      <Space align="center" style={{ marginBottom: 8 }}>
        <Title level={3} style={{ margin: 0 }}>
          知识库 Debug
        </Title>
        <Tag icon={<BugOutlined />} color="purple">
          DEV only
        </Tag>
      </Space>
      <Paragraph type="secondary">
        按文件逐步验证切块与检索。建议顺序：Q_A Excel → RFQ（.docx）→ 报价 Excel（baselines）。
        须 <Text code>MOCK_RAG=false</Text>、<Text code>nomic-embed-text</Text>、PostgreSQL。
      </Paragraph>

      {status?.mock_rag && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="MOCK_RAG=true"
          description="Debug 向量索引与检索需要 MOCK_RAG=false，并在 .env 中配置 Ollama。"
        />
      )}

      {statusLoading && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }} message="正在加载 Debug 状态..." />
      )}

      {!statusLoading && status && !status.embedding_model_ready && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="Embedding 模型未就绪"
          description={status.ollama_error || `请执行 ollama pull ${status.embedding_model}`}
        />
      )}

      {!statusLoading && status && !status.corpus_exists && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="语料目录不可访问"
          description={`容器内路径：${status.corpus_path}。请确认 docker compose 已挂载 VALIDATION_CORPUS_HOST。`}
        />
      )}

      {previewErrors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="部分文件预览失败"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {previewErrors.map((e) => (
                <li key={`${e.file}-${e.error}`}>
                  <Text code>{e.file}</Text>：{e.error}
                </li>
              ))}
            </ul>
          }
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "overview",
            label: "概览 & 索引",
            children: (
              <Card>
                <Space direction="vertical" style={{ width: "100%", marginBottom: 16 }} size="middle">
                  <Space wrap align="center">
                    <Text strong>语料文件：</Text>
                    <Select
                      style={{ minWidth: 360 }}
                      placeholder="选择要预览的文件"
                      value={selectedFile ?? undefined}
                      onChange={setSelectedFile}
                      options={corpusFiles.map((f) => ({
                        value: f.filename,
                        label: (
                          <Space>
                            <Tag color={FILE_ROLE_COLOR[f.file_role] || "default"}>
                              {FILE_ROLE_LABEL[f.file_role] || f.file_role}
                            </Tag>
                            {f.filename}
                            {!f.indexable && <Text type="secondary">（不向量化）</Text>}
                          </Space>
                        ),
                      }))}
                    />
                  </Space>
                </Space>
                <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="语料路径">{status?.corpus_path}</Descriptions.Item>
                  <Descriptions.Item label="语料存在">
                    {status?.corpus_exists ? <Tag color="green">是</Tag> : <Tag color="red">否</Tag>}
                  </Descriptions.Item>
                  <Descriptions.Item label="当前预览文件">{selectedFile || "—"}</Descriptions.Item>
                  <Descriptions.Item label="已索引 chunks">{status?.indexed_chunks ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="上次索引">{status?.last_index_at || "—"}</Descriptions.Item>
                  <Descriptions.Item label="Embedding">{status?.embedding_model}</Descriptions.Item>
                </Descriptions>
                {previewMeta?.quote_baselines && (
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                    message="报价 Excel baselines（不进向量库）"
                    description={
                      <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
                        {JSON.stringify(
                          (previewMeta.quote_baselines as { function_position_counts?: Record<string, number> })
                            .function_position_counts ?? previewMeta.quote_baselines,
                          null,
                          2,
                        )}
                      </pre>
                    }
                  />
                )}
                <Space wrap>
                  <Button
                    type="primary"
                    loading={loading === "preview"}
                    disabled={!selectedFile}
                    onClick={() => void runPreviewFile()}
                  >
                    预览选中文件
                  </Button>
                  <Button
                    loading={loading === "index"}
                    disabled={!selectedFile || !corpusFiles.find((f) => f.filename === selectedFile)?.indexable}
                    onClick={() => void runIndex()}
                  >
                    索引选中文件（pgvector + Ollama）
                  </Button>
                  <Button onClick={() => void loadStatus()}>刷新状态</Button>
                </Space>
              </Card>
            ),
          },
          {
            key: "chunks",
            label: chunkTabLabel,
            children: (
              <>
                {isBaselineBrowse && (
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="报价 Excel 不向量化"
                    description="下列为各 Function Sheet 解析出的岗位行（baselines），用于核对源 Excel；不参与 pgvector 索引与检索实验室。"
                  />
                )}
                <Table
                  rowKey="chunk_id"
                  size="small"
                  dataSource={chunks}
                  pagination={{ pageSize: 15 }}
                  locale={{
                    emptyText: isBaselineBrowse
                      ? "暂无 baselines 行：请先预览选中文件"
                      : "暂无切块：请先预览或索引 RFQ / Q_A",
                  }}
                  columns={[
                    { title: "类型", dataIndex: "chunk_type", width: 100 },
                    { title: isBaselineBrowse ? "Function" : "章节/Area", dataIndex: "chunk_chapter", width: 120, ellipsis: true },
                    {
                      title: isBaselineBrowse ? "Sum" : "字符",
                      width: 88,
                      render: (_, row) =>
                        isBaselineBrowse
                          ? String((row.metadata as Record<string, unknown> | undefined)?.sum ?? "—")
                          : row.char_count,
                    },
                    {
                      title: "预览",
                      dataIndex: "preview",
                      ellipsis: true,
                    },
                    {
                      title: "操作",
                      width: 200,
                      render: (_, row) => (
                        <Space size="small">
                          <Button size="small" onClick={() => void openChunk(row.chunk_id)}>
                            详情
                          </Button>
                          {!isBaselineBrowse && (
                            <Button size="small" onClick={() => void submitFeedback(row.chunk_id, "chunk_ok")}>
                              Golden
                            </Button>
                          )}
                        </Space>
                      ),
                    },
                  ]}
                />
              </>
            ),
          },
          {
            key: "search",
            label: "检索实验室",
            children: (
              <Card>
                {searchBlockedForQuote && (
                  <Alert
                    type="warning"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="当前选中报价 Excel — 不支持向量检索"
                    description={
                      <span>
                        人力报价走规则解析与 baselines，请先在「Baselines 浏览器」核对岗位行。检索实验室仅适用于已索引的{" "}
                        <strong>RFQ</strong> 与 <strong>Q_A</strong>。
                        <Button type="link" size="small" style={{ padding: 0, marginLeft: 8 }} onClick={() => setActiveTab("chunks")}>
                          前往 Baselines 浏览器
                        </Button>
                      </span>
                    }
                  />
                )}
                <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                  {searchDocType === "rfq" &&
                    "先选资料类型，再输入技术描述或 RFQ 片段关键词。当前仅检索 RFQ 章节切块。"}
                  {searchDocType === "qa" &&
                    "先选资料类型，再输入 Question 或关键词；建议同时选定 Area，避免短词误命中相近 Area。"}
                  {searchDocType === "all" &&
                    "混搜 RFQ + Q_A（高级调试）。R1 验收建议分别选 RFQ 或 Q_A 逐类验证。"}
                </Paragraph>
                <Space wrap style={{ marginBottom: 16 }}>
                  <Select
                    style={{ width: 180 }}
                    value={searchDocType}
                    options={SEARCH_DOC_TYPE_OPTIONS}
                    onChange={handleSearchDocTypeChange}
                    disabled={searchBlockedForQuote}
                  />
                  <Input
                    style={{ width: 320 }}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onPressEnter={() => void runSearch()}
                    placeholder={
                      searchDocType === "qa"
                        ? "完整 Question 或关键词"
                        : searchDocType === "rfq"
                          ? "RFQ 技术描述 / 章节关键词"
                          : "检索关键词"
                    }
                    disabled={searchBlockedForQuote}
                  />
                  {searchDocType === "qa" && (
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="Area 过滤（建议）"
                      style={{ minWidth: 200 }}
                      value={areaFilter}
                      onChange={setAreaFilter}
                      options={qaAreas.map((a) => ({ value: a, label: a }))}
                      maxTagCount={2}
                      disabled={searchBlockedForQuote}
                    />
                  )}
                  <InputNumber min={1} max={20} value={topK} onChange={(v) => setTopK(v ?? 5)} disabled={searchBlockedForQuote} />
                  <Button
                    type="primary"
                    loading={loading === "search"}
                    disabled={searchBlockedForQuote}
                    onClick={() => void runSearch()}
                  >
                    检索
                  </Button>
                </Space>
                <Table
                  rowKey={(r, i) => r.chunk_id || String(i)}
                  size="small"
                  dataSource={hits}
                  pagination={false}
                  columns={[
                    { title: "相似度", dataIndex: "similarity_score", width: 88, render: (v: number) => `${Math.round(v * 100)}%` },
                    { title: "chunk_id", dataIndex: "chunk_id", width: 120, ellipsis: true },
                    {
                      title: "meta",
                      width: 220,
                      render: (_, r) => {
                        const m = r.metadata || {};
                        const src = m.source_doc ? String(m.source_doc).split(/[/\\]/).pop() : "";
                        return `${m.doc_type || ""}${src ? ` · ${src}` : ""} · ${m.chunk_chapter || m.area || ""}`;
                      },
                    },
                    { title: "内容", dataIndex: "content", ellipsis: true },
                    {
                      title: "反馈",
                      width: 100,
                      render: (_, r) =>
                        r.chunk_id ? (
                          <Button size="small" onClick={() => void submitFeedback(r.chunk_id!, "irrelevant")}>
                            不相关
                          </Button>
                        ) : null,
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: "eval",
            label: "评测跑批",
            children: (
              <Card>
                <Paragraph type="secondary">
                  使用样例题集对当前索引跑批（内部验证，非 R1 签字表）。
                </Paragraph>
                <Button type="primary" loading={loading === "eval"} onClick={() => void runEval()}>
                  运行样例评测
                </Button>
                {evalSummary && (
                  <Descriptions style={{ marginTop: 16 }} column={3}>
                    <Descriptions.Item label="题数">{evalSummary.total}</Descriptions.Item>
                    <Descriptions.Item label="通过">{evalSummary.passed}</Descriptions.Item>
                    <Descriptions.Item label="通过率">{Math.round(evalSummary.pass_rate * 100)}%</Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title="Chunk 详情"
        open={!!selectedChunk}
        onCancel={() => setSelectedChunk(null)}
        footer={
          selectedChunk?.chunk_id ? (
            <Space>
              <Button onClick={() => void submitFeedback(String(selectedChunk.chunk_id), "bad_boundary")}>
                边界有问题
              </Button>
              <Button onClick={() => void submitFeedback(String(selectedChunk.chunk_id), "chunk_ok")}>
                标记 Golden
              </Button>
            </Space>
          ) : null
        }
        width={720}
      >
        {selectedChunk && (
          <>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="chunk_id">{String(selectedChunk.chunk_id)}</Descriptions.Item>
              <Descriptions.Item label="类型">{String(selectedChunk.chunk_type || "—")}</Descriptions.Item>
              <Descriptions.Item label="章节">{String(selectedChunk.chunk_chapter || "—")}</Descriptions.Item>
              {(selectedChunk.metadata as Record<string, unknown> | undefined)?.source_doc != null && (
                <Descriptions.Item label="源文件">
                  {String((selectedChunk.metadata as Record<string, unknown>).source_doc)}
                </Descriptions.Item>
              )}
              {(selectedChunk.metadata as Record<string, unknown> | undefined)?.sheet != null && (
                <Descriptions.Item label="Sheet">
                  {String((selectedChunk.metadata as Record<string, unknown>).sheet)}
                </Descriptions.Item>
              )}
              {(selectedChunk.metadata as Record<string, unknown> | undefined)?.excel_row != null && (
                <Descriptions.Item label="Excel 行号">
                  {String((selectedChunk.metadata as Record<string, unknown>).excel_row)}
                </Descriptions.Item>
              )}
            </Descriptions>
            <pre style={{ whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto", fontSize: 12 }}>
              {String(selectedChunk.content || "")}
            </pre>
          </>
        )}
      </Modal>
    </div>
  );
}
