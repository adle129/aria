"use client";

import {
  DeleteOutlined,
  EditOutlined,
  InfoCircleOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Drawer,
  Input,
  Modal,
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
import {
  INFER_DOC_TYPE_HINT,
  inferDocTypeFromFilename,
} from "@/lib/inferDocType";
import { masterDataSelectOptions } from "@/lib/masterData";
import { formatHardRefDeleteTip } from "@/lib/hardRefDeleteTip";
import {
  matchesProjectKeyword,
  PROJECT_ID_LABEL,
  PROJECT_ID_TIP,
} from "@/lib/projectIdentity";

const { Text, Paragraph } = Typography;

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

const SUPPLEMENT_ACCEPT =
  ".doc,.docx,.xlsx,.txt,.md,.pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

const CORE_DOC_TYPES: { doc_type: string; label: string }[] = [
  { doc_type: "rfq", label: "RFQ" },
  { doc_type: "qa", label: "问答清单" },
  { doc_type: "quote_manpower", label: "人力报价" },
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
  /** Fired after a project is moved to trash (index cleanup is separate from pending uploads). */
  onDeleted?: () => void;
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
  onDeleted,
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
  const [deleting, setDeleting] = useState<KnowledgeProjectTreeRow | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pendingUploadRef = useRef<{
    engagementId: string;
    /** When set (replace), use as-is; otherwise infer from filename. */
    docType?: string;
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
    async (
      engagementId: string,
      docType: string,
      file: File,
      loadingKey?: string,
    ) => {
      const key = loadingKey || `${engagementId}:${docType}`;
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

  const openFilePicker = useCallback(
    (engagementId: string, docType?: string) => {
      pendingUploadRef.current = { engagementId, docType };
      const input = fileInputRef.current;
      if (!input) return;
      input.accept = docType ? DOC_TYPE_ACCEPT[docType] || "" : SUPPLEMENT_ACCEPT;
      input.value = "";
      input.click();
    },
    [],
  );

  const onFileSelected = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      const pending = pendingUploadRef.current;
      pendingUploadRef.current = null;
      if (!file || !pending) return;
      const docType = pending.docType || inferDocTypeFromFilename(file.name);
      if (!docType) {
        message.warning(INFER_DOC_TYPE_HINT);
        return;
      }
      const loadingKey = pending.docType
        ? `${pending.engagementId}:${docType}`
        : `${pending.engagementId}:supplement`;
      void uploadDocument(pending.engagementId, docType, file, loadingKey);
    },
    [uploadDocument],
  );

  const confirmDelete = useCallback(async () => {
    if (!deleting) return;
    setDeleteSubmitting(true);
    try {
      await apiClient.delete(
        `/knowledge/engagements/${encodeURIComponent(deleting.engagement_id)}`,
      );
      message.success("已移入回收站，保留 30 天可恢复");
      setDeleting(null);
      onDeleted?.();
      await refreshAfterWrite();
    } catch (err: unknown) {
      const body = (err as { response?: { data?: { msg?: string; data?: { ref_task_ids?: string[] } } } })
        ?.response?.data;
      const refIds = body?.data?.ref_task_ids;
      const detail =
        Array.isArray(refIds) && refIds.length > 0
          ? formatHardRefDeleteTip(refIds)
          : body?.msg || "删除失败";
      message.error(detail);
    } finally {
      setDeleteSubmitting(false);
    }
  }, [deleting, onDeleted, refreshAfterWrite]);

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
            const missingTypes = CORE_DOC_TYPES.filter(
              (item) => !presentTypes.has(item.doc_type),
            );
            const canWriteDocs =
              canEdit && !writeProtected && !row.synthetic;
            type DocRowView = KnowledgeDocRow & { placeholder?: boolean };
            const docRows: DocRowView[] = [
              ...row.documents,
              ...(canWriteDocs
                ? missingTypes.map((item) => ({
                    path: `__missing__:${row.engagement_id}:${item.doc_type}`,
                    project_name: row.project_name,
                    doc_type: item.doc_type,
                    status: "pending",
                    engagement_id: row.engagement_id,
                    placeholder: true,
                  }))
                : []),
            ];
            const actionLinkStyle = { color: "rgba(0, 0, 0, 0.65)" };
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
                  {canWriteDocs && missingTypes.length > 0 ? (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      还缺 {missingTypes.map((m) => m.label).join("、")}
                      ，请在下表对应行右侧点击「补传」。
                    </Text>
                  ) : null}
                  <Table<DocRowView>
                    size="small"
                    pagination={false}
                    rowKey="path"
                    dataSource={docRows}
                    scroll={{ x: canWriteDocs ? 720 : 640 }}
                    tableLayout="fixed"
                    locale={{
                      emptyText: canWriteDocs
                        ? "该项目下暂无文档"
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
                        render: (_: unknown, doc: DocRowView) =>
                          doc.placeholder ? (
                            <Text type="secondary">未上传</Text>
                          ) : (
                            <Tooltip title={doc.path}>
                              {fileNameFromPath(doc.path)}
                            </Tooltip>
                          ),
                      },
                      {
                        title: "大小",
                        dataIndex: "file_size_bytes",
                        width: 88,
                        render: (v?: number, doc?: DocRowView) =>
                          doc?.placeholder ? "—" : formatBytes(v),
                      },
                      {
                        title: "文件时间",
                        dataIndex: "modified_at",
                        width: 160,
                        render: (v?: string | null, doc?: DocRowView) =>
                          doc?.placeholder ? "—" : formatApiTime(v),
                      },
                      {
                        title: "检索状态",
                        dataIndex: "status",
                        width: 96,
                        render: (v: string, doc: DocRowView) => {
                          if (doc.placeholder) {
                            return <Tag>待补传</Tag>;
                          }
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
                              render: (_: unknown, doc: DocRowView) => {
                                const key = `${row.engagement_id}:${doc.doc_type}`;
                                const isPlaceholder = Boolean(doc.placeholder);
                                return (
                                  <Button
                                    type="link"
                                    size="small"
                                    icon={<UploadOutlined />}
                                    loading={uploadingKey === key}
                                    disabled={Boolean(uploadingKey)}
                                    style={
                                      isPlaceholder ? undefined : actionLinkStyle
                                    }
                                    onClick={() =>
                                      openFilePicker(
                                        row.engagement_id,
                                        doc.doc_type,
                                      )
                                    }
                                  >
                                    {isPlaceholder ? "补传" : "替换"}
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
                  width: 200,
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
                    const emptyShell = row.documents.length === 0;
                    const refTaskIds = row.ref_task_ids ?? [];
                    const hasHardRefs =
                      row.has_hard_refs === true || refTaskIds.length > 0;
                    const showDelete =
                      row.deletable === true ||
                      (emptyShell && !hasHardRefs);
                    const deleteBlockedTip = hasHardRefs
                      ? formatHardRefDeleteTip(refTaskIds)
                      : !emptyShell &&
                          row.tier === "gold" &&
                          row.index_status === "indexed"
                        ? "资料齐全且可检索的项目不支持一键删除"
                        : undefined;
                    return (
                      <Space size={0} wrap>
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
                        {showDelete ? (
                          <Button
                            type="link"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            disabled={writeProtected}
                            onClick={() => setDeleting(row)}
                          >
                            删除项目
                          </Button>
                        ) : deleteBlockedTip ? (
                          <Tooltip title={deleteBlockedTip}>
                            <Button type="link" size="small" danger disabled>
                              删除项目
                            </Button>
                          </Tooltip>
                        ) : null}
                      </Space>
                    );
                  },
                },
              ]
            : []),
        ]}
      />

      <Modal
        title="删除历史项目？"
        open={Boolean(deleting)}
        onCancel={() => (deleteSubmitting ? undefined : setDeleting(null))}
        onOk={() => void confirmDelete()}
        okText="删除"
        cancelText="取消"
        okButtonProps={{ danger: true, loading: deleteSubmitting }}
        cancelButtonProps={{ disabled: deleteSubmitting }}
        destroyOnClose
      >
        <Paragraph style={{ marginBottom: 8 }}>
          将移入回收站，保留 30 天，可恢复；期间相似对标不再使用本项目。
        </Paragraph>
        {deleting ? (
          <Text type="secondary">
            {deleting.project_name} · {deleting.engagement_id}
          </Text>
        ) : null}
      </Modal>

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
