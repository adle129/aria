"use client";

import { InboxOutlined, UploadOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import axios from "axios";
import { useMemo, useState } from "react";
import { apiClient } from "@/api/client";
import {
  ENGAGEMENT_TIER_COLOR,
  ENGAGEMENT_TIER_LABEL,
  type EngagementTier,
} from "@/lib/engagementCompleteness";
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
      const packs = resp.data.data.packs;
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
        单套：上传 <Text strong>ZIP</Text>（推荐，目录内含 RFQ / Q_A / 报价 Excel），或填写{" "}
        <Text strong>Engagement ID</Text> 后一次选择多文件。单次最多 <Text strong>5</Text> 个
        ZIP，单个上传文件最多 100MB；ZIP 内单文件最多 50MB、解压总量最多
        500MB，异常压缩比和不安全路径会被拒绝。散文件模式每次 1 套。
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
        <p className="ant-upload-text">点击或拖拽 ZIP / RFQ / Q_A / 报价 Excel / manifest.json</p>
        <p className="ant-upload-hint" id="engagement-upload-hint">
          ZIP 无需填 ID；散文件须先填 Engagement ID
        </p>
      </Upload.Dragger>

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
          />
          <Table
            style={{ marginTop: 12 }}
            rowKey="engagement_id"
            size="small"
            pagination={false}
            scroll={{ x: "max-content" }}
            dataSource={lastResults}
            expandable={{
              expandedRowRender: (row) => (
                <Space direction="vertical" size={4}>
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
                  {!row.files?.length && !row.errors?.length && !row.path ? (
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
        <Space style={{ marginTop: 16 }}>
          <Button
            type="primary"
            disabled={writeProtected}
            onClick={() => {
              setShowPostUploadActions(false);
              onRequestIndex?.();
            }}
          >
            为本批建立检索索引
          </Button>
          <Button onClick={() => setShowPostUploadActions(false)}>稍后处理</Button>
        </Space>
      ) : (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          message="上传后须建立检索索引方可检索"
        />
      )}
    </Card>
  );
}
