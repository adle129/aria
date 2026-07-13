"use client";

import { InboxOutlined, UploadOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Collapse,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import axios from "axios";
import { useMemo, useState } from "react";
import { apiClient } from "@/api/client";
import EngagementMetadataForm from "@/components/EngagementMetadataForm";
import {
  ENGAGEMENT_TIER_COLOR,
  ENGAGEMENT_TIER_LABEL,
  type EngagementTier,
} from "@/lib/engagementCompleteness";
import { isEngagementMetadataComplete } from "@/lib/engagementMetadata";
import {
  formatUploadPackStatus,
  summarizeUploadPacks,
  uploadNeedsEngagementId,
  validateEngagementUpload,
} from "@/lib/engagementUpload";
import { formatCapacityBytes } from "@/lib/kbCapacity";

const { Paragraph, Text } = Typography;

export interface EngagementPackResult {
  engagement_id: string;
  project_name?: string;
  customer?: string | null;
  year?: number | null;
  functions?: string[];
  metadata_complete?: boolean;
  status: string;
  stored: boolean;
  tier: EngagementTier;
  indexable: boolean;
  missing?: string[];
  automation_impacts: string[];
  path?: string;
  files?: string[];
  errors?: Array<{ file?: string; error?: string }>;
}

interface CapacityErrorData {
  required_bytes: number;
  available_bytes: number;
  usage_percent: number;
  action: string;
}

const MISSING_LABEL: Record<string, string> = {
  rfq: "RFQ",
  qa: "Q&A",
  quote_manpower: "人力报价 Excel",
};

interface EngagementUploadPanelProps {
  onUploaded?: () => void;
  onRequestIndex?: () => void;
  writeProtected?: boolean;
}

export default function EngagementUploadPanel({
  onUploaded,
  onRequestIndex,
  writeProtected = false,
}: EngagementUploadPanelProps) {
  const [engagementId, setEngagementId] = useState("");
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [lastResults, setLastResults] = useState<EngagementPackResult[] | null>(null);
  const [showPostUploadActions, setShowPostUploadActions] = useState(false);
  const [capacityError, setCapacityError] =
    useState<CapacityErrorData | null>(null);

  const fileNames = useMemo(() => fileList.map((f) => f.name), [fileList]);
  const selectionError = useMemo(
    () =>
      validateEngagementUpload(
        fileList.map((file) => ({
          name: file.name,
          size: file.size ?? 0,
        })),
      ),
    [fileList],
  );
  const needsEngagementId = uploadNeedsEngagementId(fileNames);
  const zipCount = fileNames.filter((n) => n.toLowerCase().endsWith(".zip")).length;
  const summary = useMemo(
    () => (lastResults ? summarizeUploadPacks(lastResults) : null),
    [lastResults],
  );

  const handleUpload = async () => {
    if (writeProtected) {
      message.error("数据盘处于写保护，暂时无法上传");
      return;
    }
    if (!fileList.length) {
      message.warning("请选择 ZIP 或项目文件");
      return;
    }
    if (selectionError) {
      message.warning(selectionError);
      return;
    }
    if (needsEngagementId && !engagementId.trim()) {
      message.warning("散文件上传须填写 Engagement ID（项目目录名）");
      return;
    }
    if (!needsEngagementId && zipCount > 5) {
      message.warning("单次最多上传 5 个 ZIP 项目包");
      return;
    }
    if (needsEngagementId && fileList.length > 0 && zipCount > 0) {
      message.warning("请勿同时上传 ZIP 与散文件");
      return;
    }
    if (replaceExisting) {
      const confirmed = await new Promise<boolean>((resolve) => {
        Modal.confirm({
          title: "确认替换同 ID 项目？",
          content: "新项目包校验通过后将整体替换旧目录；不会合并旧文件。",
          okText: "确认替换",
          okButtonProps: { danger: true },
          cancelText: "取消",
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        });
      });
      if (!confirmed) return;
    }

    const form = new FormData();
    for (const f of fileList) {
      if (f.originFileObj) {
        form.append("files", f.originFileObj, f.name);
      }
    }
    if (needsEngagementId) {
      form.append("engagement_id", engagementId.trim());
    }
    form.append("replace_existing", String(replaceExisting));

    setUploading(true);
    setCapacityError(null);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: { packs: EngagementPackResult[]; uploaded: number };
      }>("/knowledge/engagements/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const packs = resp.data.data.packs.map((pack) => ({
        ...pack,
        metadata_complete: isEngagementMetadataComplete({
          project_name: pack.project_name,
          customer: pack.customer,
          year: pack.year,
          functions: pack.functions,
        }),
      }));
      setLastResults(packs);
      const counts = summarizeUploadPacks(packs);
      if (counts.failed > 0) {
        message.warning(
          `已处理 ${resp.data.data.uploaded} 套：失败 ${counts.failed}，不完整 ${counts.incomplete}，可索引 ${counts.indexable}`,
        );
      } else if (counts.incomplete > 0) {
        message.info(
          `已上传 ${counts.stored} 套：不完整 ${counts.incomplete}，可索引 ${counts.indexable}`,
        );
      } else {
        message.success(`已上传 ${counts.stored} 套，可建立检索索引`);
      }
      setShowPostUploadActions(counts.stored > 0);
      setFileList([]);
      setReplaceExisting(false);
      onUploaded?.();
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 507) {
        setCapacityError(error.response.data?.data ?? null);
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card title="上传项目包" style={{ marginBottom: 16 }} size="small">
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        单套：上传 <Text strong>ZIP</Text>（推荐，目录内含 RFQ / Q&A / 报价 Excel），或填写{" "}
        <Text strong>Engagement ID</Text> 后一次选择多文件。单次最多 <Text strong>5</Text> 个
        ZIP。落盘后须填写项目信息（显示名、客户、年份、工程领域）再建立索引。
      </Paragraph>

      {selectionError && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="当前选择无法上传"
          description={`${selectionError}。请调整文件后重试。`}
        />
      )}

      {capacityError && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 12 }}
          role="alert"
          aria-live="assertive"
          message="上传所需空间不足"
          description={`需要保留 ${formatCapacityBytes(capacityError.required_bytes)}，当前可用 ${formatCapacityBytes(capacityError.available_bytes)}（使用率 ${capacityError.usage_percent}%）。请清理数据盘或联系 IT 扩容后再试。${capacityError.action ? `（${capacityError.action}）` : ""}`}
        />
      )}

      {needsEngagementId && (
        <Space style={{ marginBottom: 12 }} wrap>
          <Text>Engagement ID：</Text>
          <Input
            style={{ width: 280 }}
            placeholder="如 dev_chassis_2024"
            value={engagementId}
            disabled={writeProtected}
            onChange={(e) => setEngagementId(e.target.value)}
          />
        </Space>
      )}

      <Upload.Dragger
        multiple
        disabled={writeProtected}
        fileList={fileList}
        beforeUpload={() => false}
        onChange={({ fileList: next }) => setFileList(next)}
        accept=".zip,.docx,.doc,.xlsx,.json"
        aria-describedby="engagement-upload-hint"
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽 ZIP，或 RFQ / Q&A / 报价文件</p>
        <p className="ant-upload-hint" id="engagement-upload-hint">
          ZIP 无需填 ID；散文件须先填 Engagement ID。项目说明由系统自动生成。
        </p>
      </Upload.Dragger>

      <Collapse
        ghost
        style={{ marginTop: 8 }}
        items={[
          {
            key: "advanced",
            label: <Text type="secondary">高级：自带项目说明文件（可选）</Text>,
            children: (
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                IT 批量包可包含 <Text code>manifest.json</Text>
                ；日常上传无需准备。若上传了该文件，将与系统推断结果合并。
              </Paragraph>
            ),
          },
        ]}
      />

      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          loading={uploading}
          disabled={!fileList.length || writeProtected || Boolean(selectionError)}
          onClick={() => void handleUpload()}
        >
          上传并落盘
        </Button>
        <Button onClick={() => setFileList([])} disabled={!fileList.length || uploading}>
          清空选择
        </Button>
        <Checkbox
          checked={replaceExisting}
          disabled={uploading || writeProtected}
          onChange={(event) => setReplaceExisting(event.target.checked)}
        >
          替换同 ID 项目
        </Checkbox>
      </Space>

      {replaceExisting && (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 12 }}
          message="替换模式不会合并文件；新包校验通过后整体替换旧项目"
        />
      )}

      {summary && lastResults && lastResults.length > 0 && (
        <>
          <Alert
            type={summary.failed ? "warning" : "success"}
            showIcon
            style={{ marginTop: 16 }}
            aria-live="polite"
            message={`本批结果：成功落盘 ${summary.stored}，可索引 ${summary.indexable}，资料不完整 ${summary.incomplete}，失败 ${summary.failed}`}
            description="展开行完善项目信息（必填）后，再为本批建立检索索引。"
          />
          <Table
            style={{ marginTop: 12 }}
            rowKey="engagement_id"
            size="small"
            pagination={false}
            scroll={{ x: "max-content" }}
            dataSource={lastResults}
            expandable={{
              defaultExpandAllRows: true,
              expandedRowRender: (row) => (
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  {row.path ? <Text type="secondary">路径：{row.path}</Text> : null}
                  {row.files?.length ? (
                    <Text type="secondary">文件：{row.files.join("、")}</Text>
                  ) : null}
                  {row.errors?.length ? (
                    <Text type="danger">
                      错误：
                      {row.errors
                        .map((e) => `${e.file || "—"}：${e.error || "未知错误"}`)
                        .join("；")}
                    </Text>
                  ) : null}
                  {row.stored ? (
                    <EngagementMetadataForm
                      engagementId={row.engagement_id}
                      compact
                      disabled={writeProtected}
                      initial={{
                        project_name: row.project_name,
                        customer: row.customer,
                        year: row.year,
                        functions: row.functions,
                      }}
                      onSaved={(next) => {
                        setLastResults((prev) =>
                          (prev || []).map((item) =>
                            item.engagement_id === row.engagement_id
                              ? {
                                  ...item,
                                  project_name: next.project_name,
                                  customer: next.customer,
                                  year: next.year,
                                  functions: next.functions,
                                  metadata_complete:
                                    next.metadata_complete ??
                                    isEngagementMetadataComplete(next),
                                }
                              : item,
                          ),
                        );
                        onUploaded?.();
                      }}
                    />
                  ) : !row.files?.length && !row.errors?.length && !row.path ? (
                    <Text type="secondary">无更多详情</Text>
                  ) : null}
                </Space>
              ),
            }}
            columns={[
              { title: "项目目录名", dataIndex: "engagement_id", width: 160 },
              { title: "项目名称", dataIndex: "project_name", ellipsis: true },
              {
                title: "资料完整度",
                key: "tier",
                width: 72,
                render: (_: unknown, row: EngagementPackResult) => (
                  <Tag color={ENGAGEMENT_TIER_COLOR[row.tier]}>
                    {ENGAGEMENT_TIER_LABEL[row.tier]}
                  </Tag>
                ),
              },
              {
                title: "项目信息",
                key: "metadata",
                width: 120,
                render: (_: unknown, row: EngagementPackResult) =>
                  row.stored && !row.metadata_complete ? (
                    <Tooltip title="请填写客户、年份与工程领域后再建立索引">
                      <Tag color="warning">待完善</Tag>
                    </Tooltip>
                  ) : row.stored ? (
                    <Tag color="success">已完善</Tag>
                  ) : (
                    "—"
                  ),
              },
              {
                title: "状态",
                key: "upload_status",
                width: 168,
                render: (_: unknown, row: EngagementPackResult) => {
                  const view = formatUploadPackStatus(row);
                  return <Tag color={view.color}>{view.label}</Tag>;
                },
              },
              {
                title: "缺件",
                dataIndex: "missing",
                render: (missing: string[] | undefined) =>
                  missing?.length
                    ? missing.map((m) => MISSING_LABEL[m] || m).join("、")
                    : "—",
              },
              {
                title: "自动化影响",
                key: "impact",
                render: (_: unknown, row: EngagementPackResult) =>
                  row.automation_impacts.length
                    ? row.automation_impacts.join("；")
                    : row.stored
                      ? "三件套齐全，可支撑 R1 检索与后续里程碑"
                      : "—",
              },
            ]}
          />
        </>
      )}

      {showPostUploadActions && summary && summary.stored > 0 ? (
        <Space style={{ marginTop: 16 }} direction="vertical" size={8}>
          {lastResults?.some((p) => p.stored && !p.metadata_complete) ? (
            <Alert
              type="warning"
              showIcon
              message="请先保存每套项目的完整项目信息（客户、年份、工程领域），再建立索引"
            />
          ) : null}
          <Space>
            <Button
              type="primary"
              disabled={
                writeProtected ||
                Boolean(lastResults?.some((p) => p.stored && !p.metadata_complete))
              }
              onClick={() => {
                setShowPostUploadActions(false);
                onRequestIndex?.();
              }}
            >
              为本批建立检索索引
            </Button>
            <Button onClick={() => setShowPostUploadActions(false)}>稍后处理</Button>
          </Space>
        </Space>
      ) : (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          message="上传并完善项目信息后，须建立检索索引方可检索"
        />
      )}
    </Card>
  );
}
