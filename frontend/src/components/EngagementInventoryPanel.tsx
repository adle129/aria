"use client";

import { EditOutlined, InfoCircleOutlined, UploadOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Drawer,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ReactNode,
} from "react";
import {
  apiClient,
  listCustomers,
  listVehicleModels,
  type MasterDataItem,
} from "@/api/client";
import EngagementMetadataForm from "@/components/EngagementMetadataForm";
import { parseApiTimestamp } from "@/lib/apiTime";
import {
  formatEngagementIndexStatus,
  formatEngagementTier,
} from "@/lib/engagementCompleteness";
import {
  formatEngagementMetadataSummary,
  isEngagementMetadataComplete,
} from "@/lib/engagementMetadata";
import {
  buildKnowledgeProjectTree,
  type KnowledgeDocRow,
  type KnowledgeEngagementRow,
  type KnowledgeProjectTreeRow,
} from "@/lib/knowledgeProjectTree";
import { masterDataSelectOptions } from "@/lib/masterData";
import {
  matchesProjectKeyword,
  PROJECT_ID_LABEL,
  PROJECT_ID_TIP,
} from "@/lib/projectIdentity";

const { Text } = Typography;

const DOC_TYPE_LABEL: Record<string, string> = {
  rfq: "RFQ",
  qa: "QA 清单",
  quote_manpower: "人力报价",
  summary: "方案摘要",
};

const DOC_TYPE_ACCEPT: Record<string, string> = {
  rfq: ".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  qa: ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  quote_manpower:
    ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  summary: ".doc,.docx,.txt,.md,.pdf",
};

const SUPPLEMENT_TYPES: { doc_type: string; label: string }[] = [
  { doc_type: "rfq", label: "补传 RFQ" },
  { doc_type: "qa", label: "补传问答" },
  { doc_type: "quote_manpower", label: "补传报价" },
];

const SAVE_REINDEX_TIP = "已保存。请点击上方「更新检索」后才会用于相似项目对标。";

const DOC_STATUS_TAG: Record<string, { color: string; label: string }> = {
  indexed: { color: "green", label: "可检索" },
  pending: { color: "default", label: "待更新" },
  failed: { color: "red", label: "失败" },
};

function formatApiTime(value?: string | null): string {
  const ts = parseApiTimestamp(value);
  if (Number.isNaN(ts)) return "—";
  return new Date(ts).toLocaleString();
}

function formatBytes(n?: number): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fileNameFromPath(path: string): string {
  const parts = path.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || path;
}

function ColumnTitle({ title, tip }: { title: string; tip: string }) {
  return (
    <Tooltip title={tip}>
      <Space size={4}>
        <span>{title}</span>
        <InfoCircleOutlined style={{ color: "#999", fontSize: 12 }} />
      </Space>
    </Tooltip>
  );
}

interface EngagementInventoryPanelProps {
  refreshToken?: number;
  canEdit?: boolean;
  writeProtected?: boolean;
  /** When provided, parent owns document list (shared refresh with page). */
  documents?: KnowledgeDocRow[];
  documentsLoading?: boolean;
  emptyText?: string;
  /** Extra controls in card header (e.g. page toolbar actions). */
  headerExtra?: ReactNode;
  hideBuiltinRefresh?: boolean;
  /** Parent refresh after document upsert (documents + engagements). */
  onChanged?: () => void | Promise<void>;
}

export default function EngagementInventoryPanel({
  refreshToken = 0,
  canEdit = false,
  writeProtected = false,
  documents: documentsProp,
  documentsLoading = false,
  emptyText,
  headerExtra,
  hideBuiltinRefresh = false,
  onChanged,
}: EngagementInventoryPanelProps) {
  const [engagements, setEngagements] = useState<KnowledgeEngagementRow[]>([]);
  const [localDocuments, setLocalDocuments] = useState<KnowledgeDocRow[]>([]);
  const [loadingEng, setLoadingEng] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [editing, setEditing] = useState<KnowledgeProjectTreeRow | null>(null);
  const [filterCustomer, setFilterCustomer] = useState<string | undefined>();
  const [filterVehicle, setFilterVehicle] = useState<string | undefined>();
  const [keyword, setKeyword] = useState("");
  const [customers, setCustomers] = useState<MasterDataItem[]>([]);
  const [vehicleModels, setVehicleModels] = useState<MasterDataItem[]>([]);
  const [uploadingKey, setUploadingKey] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pendingUploadRef = useRef<{
    engagementId: string;
    docType: string;
  } | null>(null);

  const loadEngagements = useCallback(async () => {
    setLoadingEng(true);
    try {
      const resp = await apiClient.get<{
        code: number;
        data: { engagements: KnowledgeEngagementRow[] };
      }>("/knowledge/engagements", {
        params: {
          customer: filterCustomer || undefined,
          vehicle_model: filterVehicle || undefined,
        },
      });
      setEngagements(resp.data.data.engagements ?? []);
    } catch {
      setEngagements([]);
    } finally {
      setLoadingEng(false);
    }
  }, [filterCustomer, filterVehicle]);

  useEffect(() => {
    void (async () => {
      try {
        const [c, v] = await Promise.all([listCustomers(true), listVehicleModels(true)]);
        setCustomers(c);
        setVehicleModels(v);
      } catch {
        setCustomers([]);
        setVehicleModels([]);
      }
    })();
  }, []);

  const loadDocuments = useCallback(async () => {
    if (documentsProp !== undefined) return;
    setLoadingDocs(true);
    try {
      const resp = await apiClient.get<{
        code: number;
        data: { documents: KnowledgeDocRow[] };
      }>("/knowledge/documents");
      setLocalDocuments(resp.data.data.documents ?? []);
    } catch {
      setLocalDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, [documentsProp]);

  useEffect(() => {
    void loadEngagements();
    void loadDocuments();
  }, [loadEngagements, loadDocuments, refreshToken]);

  const documents = documentsProp ?? localDocuments;
  const tree = useMemo(() => {
    const built = buildKnowledgeProjectTree(engagements, documents);
    if (!keyword.trim()) return built;
    return built.filter((row) => matchesProjectKeyword(row, keyword));
  }, [engagements, documents, keyword]);

  const loading = loadingEng || (documentsProp !== undefined ? documentsLoading : loadingDocs);

  const refreshAfterWrite = useCallback(async () => {
    if (onChanged) {
      await onChanged();
      return;
    }
    await Promise.all([loadEngagements(), loadDocuments()]);
  }, [onChanged, loadEngagements, loadDocuments]);

  const uploadDocument = useCallback(
    async (engagementId: string, docType: string, file: File) => {
      const key = `${engagementId}:${docType}`;
      setUploadingKey(key);
      try {
        const form = new FormData();
        form.append("doc_type", docType);
        form.append("replace", "true");
        form.append("file", file);
        await apiClient.post(
          `/knowledge/engagements/${encodeURIComponent(engagementId)}/documents`,
          form,
          { headers: { "Content-Type": "multipart/form-data" } },
        );
        message.success(SAVE_REINDEX_TIP);
        await refreshAfterWrite();
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
          "文件保存失败";
        message.error(detail);
      } finally {
        setUploadingKey(null);
      }
    },
    [refreshAfterWrite],
  );

  const openFilePicker = useCallback((engagementId: string, docType: string) => {
    pendingUploadRef.current = { engagementId, docType };
    const input = fileInputRef.current;
    if (!input) return;
    input.accept = DOC_TYPE_ACCEPT[docType] || "";
    input.value = "";
    input.click();
  }, []);

  const onFileSelected = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      const pending = pendingUploadRef.current;
      pendingUploadRef.current = null;
      if (!file || !pending) return;
      void uploadDocument(pending.engagementId, pending.docType, file);
    },
    [uploadDocument],
  );

  return (
    <Card
      title="历史项目"
      size="small"
      style={{ marginBottom: 16 }}
      extra={
        <Space size={12} wrap>
          {headerExtra}
          {!hideBuiltinRefresh ? (
            <Button
              size="small"
              loading={loading}
              onClick={() => {
                void loadEngagements();
                void loadDocuments();
              }}
            >
              刷新
            </Button>
          ) : null}
        </Space>
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: "none" }}
        onChange={onFileSelected}
      />
      <Space wrap style={{ marginBottom: 12 }} size={8}>
        <Input.Search
          allowClear
          placeholder={`搜索显示名 / ${PROJECT_ID_LABEL} / 客户 / 车型`}
          style={{ width: 280 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onSearch={setKeyword}
        />
        <Select
          allowClear
          showSearch
          placeholder="按客户筛选"
          style={{ minWidth: 160 }}
          value={filterCustomer}
          options={masterDataSelectOptions(customers, { includeInactive: true })}
          optionFilterProp="label"
          onChange={(v) => setFilterCustomer(v)}
        />
        <Select
          allowClear
          showSearch
          placeholder="按车型筛选"
          style={{ minWidth: 140 }}
          value={filterVehicle}
          options={masterDataSelectOptions(vehicleModels, { includeInactive: true })}
          optionFilterProp="label"
          onChange={(v) => setFilterVehicle(v)}
        />
      </Space>
      <Text type="secondary" style={{ display: "block", marginBottom: 10, fontSize: 12 }}>
        显示名可重复；同客户同车型靠「{PROJECT_ID_LABEL}」区分。可直接搜索编号定位项目。
      </Text>
      <Table<KnowledgeProjectTreeRow>
        size="small"
        rowKey="engagement_id"
        loading={loading}
        dataSource={tree}
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
        scroll={{ x: "max-content" }}
        locale={{
          emptyText: emptyText || "暂无历史项目；请「添加历史项目」或由 IT 落盘后更新检索",
        }}
        expandable={{
          expandedRowRender: (row) => {
            const metaComplete =
              row.metadata_complete ??
              isEngagementMetadataComplete({
                project_name: row.project_name,
                customer: row.customer,
                year: row.year,
                functions: row.functions,
              });
            const staleIncompleteError =
              Boolean(row.last_error) &&
              /信息不完整|项目信息未齐|需填写项目显示名/i.test(row.last_error || "");
            const presentTypes = new Set(row.documents.map((d) => d.doc_type));
            const missingActions = SUPPLEMENT_TYPES.filter(
              (item) => !presentTypes.has(item.doc_type),
            );
            const canWriteDocs =
              canEdit && !writeProtected && !row.synthetic;
            return (
              <div style={{ padding: "4px 0 8px" }}>
                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                  {row.last_error && row.index_status === "failed" ? (
                    metaComplete && staleIncompleteError ? (
                      <Text type="secondary" style={{ fontSize: 13 }}>
                        项目信息已完善，请再次点击上方「更新检索」写入检索库。
                      </Text>
                    ) : (
                      <Text type="danger" style={{ fontSize: 13 }}>
                        失败原因：{row.last_error}
                      </Text>
                    )
                  ) : null}
                  {row.uploaded_at ? (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      项目落盘时间：{formatApiTime(row.uploaded_at)}
                    </Text>
                  ) : null}
                  {canWriteDocs && missingActions.length > 0 ? (
                    <Space wrap size={8}>
                      {missingActions.map((item) => {
                        const key = `${row.engagement_id}:${item.doc_type}`;
                        return (
                          <Button
                            key={item.doc_type}
                            size="small"
                            icon={<UploadOutlined />}
                            loading={uploadingKey === key}
                            disabled={Boolean(uploadingKey)}
                            onClick={() =>
                              openFilePicker(row.engagement_id, item.doc_type)
                            }
                          >
                            {item.label}
                          </Button>
                        );
                      })}
                    </Space>
                  ) : null}
                  <Table<KnowledgeDocRow>
                    size="small"
                    pagination={false}
                    rowKey="path"
                    dataSource={row.documents}
                    scroll={{ x: canWriteDocs ? 720 : 640 }}
                    tableLayout="fixed"
                    locale={{
                      emptyText: canWriteDocs
                        ? "该项目下暂无文档，可使用上方「补传」或「添加历史项目」"
                        : "该项目下暂无文档，请通过「添加历史项目」补充",
                    }}
                    columns={[
                      {
                        title: "类型",
                        dataIndex: "doc_type",
                        width: 88,
                        render: (v: string) => DOC_TYPE_LABEL[v] || v,
                      },
                      {
                        title: "文件名",
                        key: "file_name",
                        width: 180,
                        ellipsis: true,
                        render: (_: unknown, doc: KnowledgeDocRow) => (
                          <Tooltip title={doc.path}>{fileNameFromPath(doc.path)}</Tooltip>
                        ),
                      },
                      {
                        title: "大小",
                        dataIndex: "file_size_bytes",
                        width: 88,
                        render: (v?: number) => formatBytes(v),
                      },
                      {
                        title: "文件时间",
                        dataIndex: "modified_at",
                        width: 160,
                        render: (v?: string | null) => formatApiTime(v),
                      },
                      {
                        title: "检索状态",
                        dataIndex: "status",
                        width: 96,
                        render: (v: string, doc: KnowledgeDocRow) => {
                          const cfg = DOC_STATUS_TAG[v] || {
                            color: "default",
                            label: v || "等待",
                          };
                          return (
                            <Tooltip title={doc.error || undefined}>
                              <Tag color={cfg.color}>{cfg.label}</Tag>
                            </Tooltip>
                          );
                        },
                      },
                      ...(canWriteDocs
                        ? [
                            {
                              title: "操作",
                              key: "doc_actions",
                              width: 88,
                              render: (_: unknown, doc: KnowledgeDocRow) => {
                                const key = `${row.engagement_id}:${doc.doc_type}`;
                                return (
                                  <Button
                                    type="link"
                                    size="small"
                                    icon={<UploadOutlined />}
                                    loading={uploadingKey === key}
                                    disabled={Boolean(uploadingKey)}
                                    onClick={() =>
                                      openFilePicker(row.engagement_id, doc.doc_type)
                                    }
                                  >
                                    替换
                                  </Button>
                                );
                              },
                            },
                          ]
                        : []),
                    ]}
                  />
                </Space>
              </div>
            );
          },
        }}
        columns={[
          {
            title: "项目名称",
            dataIndex: "project_name",
            render: (name: string, row) => (
              <Space size={6}>
                <span>{name}</span>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {row.documents.length} 个文档
                </Text>
                {row.synthetic ? (
                  <Tooltip title="仅见文档清单、未见项目登记；完善入库后将合并显示">
                    <Tag style={{ margin: 0 }}>未登记</Tag>
                  </Tooltip>
                ) : null}
              </Space>
            ),
          },
          {
            title: (
              <ColumnTitle title={PROJECT_ID_LABEL} tip={PROJECT_ID_TIP} />
            ),
            dataIndex: "engagement_id",
            width: 140,
            render: (id: string, row) =>
              row.synthetic && id.startsWith("orphan:") ? (
                "—"
              ) : (
                <Typography.Text copyable={{ text: id }} style={{ fontSize: 13 }}>
                  {id}
                </Typography.Text>
              ),
          },
          {
            title: (
              <ColumnTitle
                title="资料完整度"
                tip="按 RFQ、问答清单、人力报价是否齐全划分：金级（齐全）、银级（缺报价）、铜级（缺问答或多项）。"
              />
            ),
            dataIndex: "tier",
            render: (tier: string | null | undefined) => {
              const formatted = formatEngagementTier(tier);
              return (
                <Tooltip title={formatted.tip}>
                  <Tag color={formatted.color}>{formatted.label}</Tag>
                </Tooltip>
              );
            },
          },
          {
            title: (
              <ColumnTitle
                title="项目信息"
                tip="客户 · 车型 · 年份 · 工程领域。用于筛选与 RFQ 对比表头；同客户同车型可有多套，靠项目编号区分。"
              />
            ),
            key: "metadata",
            render: (_: unknown, row: KnowledgeProjectTreeRow) => {
              const complete =
                row.metadata_complete ??
                isEngagementMetadataComplete({
                  project_name: row.project_name,
                  customer: row.customer,
                  year: row.year,
                  functions: row.functions,
                });
              return (
                <Space size={4} wrap>
                  {!complete && !row.synthetic ? (
                    <Tooltip title="请完善客户、年份与工程领域">
                      <Tag color="warning">待完善</Tag>
                    </Tooltip>
                  ) : null}
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatEngagementMetadataSummary(row)}
                  </Text>
                </Space>
              );
            },
          },
          {
            title: (
              <ColumnTitle
                title="检索可用性"
                tip="该项目能否出现在 RFQ「相似历史项目」结果中。"
              />
            ),
            dataIndex: "index_status",
            render: (status: string, row: KnowledgeProjectTreeRow) => {
              const formatted = formatEngagementIndexStatus(status, {
                lastError: row.last_error,
              });
              return (
                <Tooltip title={formatted.tip}>
                  <Tag color={formatted.color} style={{ cursor: "help" }}>
                    {formatted.label}
                  </Tag>
                </Tooltip>
              );
            },
          },
          {
            title: "最近更新",
            dataIndex: "last_indexed_at",
            width: 160,
            render: formatApiTime,
          },
          ...(canEdit
            ? [
                {
                  title: "操作",
                  key: "actions",
                  width: 120,
                  render: (_: unknown, row: KnowledgeProjectTreeRow) => {
                    if (row.synthetic) {
                      return (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          —
                        </Text>
                      );
                    }
                    const complete =
                      row.metadata_complete ??
                      isEngagementMetadataComplete({
                        project_name: row.project_name,
                        customer: row.customer,
                        year: row.year,
                        functions: row.functions,
                      });
                    return (
                      <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        disabled={writeProtected}
                        danger={!complete}
                        style={
                          complete
                            ? { color: "rgba(0, 0, 0, 0.45)" }
                            : undefined
                        }
                        onClick={() => setEditing(row)}
                      >
                        {complete ? "编辑信息" : "完善信息"}
                      </Button>
                    );
                  },
                },
              ]
            : []),
        ]}
      />

      <Drawer
        title={
          editing
            ? `${
                (
                  editing.metadata_complete ??
                  isEngagementMetadataComplete({
                    project_name: editing.project_name,
                    customer: editing.customer,
                    year: editing.year,
                    functions: editing.functions,
                  })
                )
                  ? "编辑项目信息"
                  : "完善项目信息"
              } · ${editing.engagement_id}`
            : "完善项目信息"
        }
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        width={Math.min(480, typeof window !== "undefined" ? window.innerWidth - 24 : 480)}
        destroyOnClose
      >
        {editing && !editing.synthetic ? (
          <EngagementMetadataForm
            engagementId={editing.engagement_id}
            disabled={writeProtected}
            initial={{
              project_name: editing.project_name,
              customer: editing.customer,
              vehicle_model: editing.vehicle_model,
              year: editing.year,
              functions: editing.functions,
            }}
            onSaved={() => {
              setEditing(null);
              void loadEngagements();
            }}
          />
        ) : null}
      </Drawer>
    </Card>
  );
}
