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
  Steps,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import axios from "axios";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "@/api/client";
import EngagementMetadataForm from "@/components/EngagementMetadataForm";
import { type EngagementTier } from "@/lib/engagementCompleteness";
import { isEngagementMetadataComplete } from "@/lib/engagementMetadata";
import {
  formatUploadPackStatus,
  summarizeUploadPacks,
  uploadNeedsEngagementId,
  validateEngagementUpload,
} from "@/lib/engagementUpload";
import { formatCapacityBytes } from "@/lib/kbCapacity";

const { Text } = Typography;

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

interface EngagementUploadPanelProps {
  onUploaded?: () => void;
  onRequestIndex?: () => void;
  writeProtected?: boolean;
  /** plain = no Card wrapper (for Drawer body). */
  variant?: "card" | "plain";
  /** True while any stored pack still lacks project_name/customer/year/functions. */
  onMetadataIncompleteChange?: (incomplete: boolean) => void;
}

export default function EngagementUploadPanel({
  onUploaded,
  onRequestIndex,
  writeProtected = false,
  variant = "card",
  onMetadataIncompleteChange,
}: EngagementUploadPanelProps) {
  const [engagementId, setEngagementId] = useState("");
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [lastResults, setLastResults] = useState<EngagementPackResult[] | null>(null);
  const [showPostUploadActions, setShowPostUploadActions] = useState(false);
  const [capacityError, setCapacityError] =
    useState<CapacityErrorData | null>(null);
  const metadataStepRef = useRef<HTMLDivElement | null>(null);

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
  const storedPacks = useMemo(
    () => (lastResults || []).filter((p) => p.stored),
    [lastResults],
  );
  const failedPacks = useMemo(
    () => (lastResults || []).filter((p) => !p.stored),
    [lastResults],
  );
  const metadataIncomplete = useMemo(
    () => storedPacks.some((p) => !p.metadata_complete),
    [storedPacks],
  );
  /** 0 上传资料 → 1 完善信息 → 2 更新检索 */
  const flowStep = useMemo(() => {
    if (!storedPacks.length) return 0;
    if (metadataIncomplete) return 1;
    return 2;
  }, [storedPacks.length, metadataIncomplete]);

  useEffect(() => {
    onMetadataIncompleteChange?.(metadataIncomplete && storedPacks.length > 0);
  }, [metadataIncomplete, storedPacks.length, onMetadataIncompleteChange]);

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
      const needMeta = packs.some(
        (p) =>
          p.stored &&
          !isEngagementMetadataComplete({
            project_name: p.project_name,
            customer: p.customer,
            year: p.year,
            functions: p.functions,
          }),
      );
      if (counts.failed > 0) {
        message.warning(
          `已处理 ${resp.data.data.uploaded} 套：失败 ${counts.failed}；请完善成功落盘项目的信息`,
        );
      } else if (needMeta) {
        message.info(`已落盘 ${counts.stored} 套，请填写下方项目信息后再更新检索`);
      } else {
        message.success(`已上传 ${counts.stored} 套，项目信息已齐全，可更新检索`);
      }
      setShowPostUploadActions(counts.stored > 0);
      setFileList([]);
      setReplaceExisting(false);
      onUploaded?.();
      window.setTimeout(() => {
        metadataStepRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 507) {
        setCapacityError(error.response.data?.data ?? null);
      }
    } finally {
      setUploading(false);
    }
  };

  const showUploadZone = storedPacks.length === 0;

  const body = (
    <>
      <Steps
        size="small"
        current={flowStep}
        style={{ marginBottom: 12 }}
        items={[
          { title: "上传资料" },
          { title: "完善信息" },
          { title: "更新检索" },
        ]}
      />

      {showUploadZone ? (
        <>
          {selectionError && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 8 }}
              message={selectionError}
            />
          )}

          {capacityError && (
            <Alert
              type="error"
              showIcon
              style={{ marginBottom: 8 }}
              role="alert"
              aria-live="assertive"
              message="磁盘空间不足，无法上传"
              description={`需保留 ${formatCapacityBytes(capacityError.required_bytes)}，可用 ${formatCapacityBytes(capacityError.available_bytes)}。`}
            />
          )}

          {needsEngagementId && (
            <Space style={{ marginBottom: 8 }} wrap>
              <Text>项目 ID</Text>
              <Input
                style={{ width: 260 }}
                placeholder="散文件必填，如 dev_chassis_2024"
                value={engagementId}
                disabled={writeProtected}
                onChange={(e) => setEngagementId(e.target.value)}
              />
            </Space>
          )}

          <div className="engagement-upload-compact">
            <style>{`
              .engagement-upload-compact .ant-upload.ant-upload-drag {
                height: 72px !important;
                max-height: 72px !important;
                padding: 6px 10px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
              }
              .engagement-upload-compact .ant-upload-drag-icon {
                margin: 0 !important;
                line-height: 1 !important;
              }
              .engagement-upload-compact .ant-upload-drag-icon .anticon {
                font-size: 22px !important;
              }
              .engagement-upload-compact .ant-upload-text {
                margin: 0 !important;
                font-size: 13px !important;
              }
              .engagement-upload-compact .ant-upload-hint {
                margin: 0 !important;
                font-size: 12px !important;
              }
              .engagement-upload-compact .ant-upload-list {
                margin-top: 6px;
                max-height: 72px;
                overflow: auto;
              }
            `}</style>
            <Upload.Dragger
              multiple
              disabled={writeProtected}
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: next }) => setFileList(next)}
              accept=".zip,.docx,.doc,.xlsx,.json"
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">拖拽或选择 ZIP（推荐）</p>
              <p className="ant-upload-hint">也可选 RFQ / Q&A / 报价文件 · 最多 5 个 ZIP</p>
            </Upload.Dragger>
          </div>

          <Space style={{ marginTop: 10 }} wrap>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              loading={uploading}
              disabled={!fileList.length || writeProtected || Boolean(selectionError)}
              onClick={() => void handleUpload()}
            >
              上传并保存
            </Button>
            <Button onClick={() => setFileList([])} disabled={!fileList.length || uploading}>
              清空
            </Button>
            <Checkbox
              checked={replaceExisting}
              disabled={uploading || writeProtected}
              onChange={(event) => setReplaceExisting(event.target.checked)}
            >
              替换同 ID
            </Checkbox>
          </Space>
          {replaceExisting ? (
            <Text type="secondary" style={{ display: "block", marginTop: 6, fontSize: 12 }}>
              替换：新包校验通过后整体覆盖旧项目，不合并文件。
            </Text>
          ) : null}
        </>
      ) : (
        <div style={{ marginBottom: 10 }}>
          <Space wrap size={8}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              已保存 {summary?.stored ?? storedPacks.length} 套资料
            </Text>
            <Button
              type="link"
              size="small"
              style={{ padding: 0, height: "auto" }}
              onClick={() => {
                setLastResults(null);
                setShowPostUploadActions(false);
                setFileList([]);
              }}
            >
              继续添加
            </Button>
          </Space>
        </div>
      )}

      {failedPacks.length > 0 ? (
        <Space direction="vertical" size={4} style={{ width: "100%", marginBottom: 8 }}>
          {failedPacks.map((row) => (
            <Alert
              key={row.engagement_id}
              type="error"
              showIcon
              message={`${row.engagement_id} 失败`}
              description={
                row.errors?.length
                  ? row.errors
                      .map((e) => `${e.file || "—"}：${e.error || "未知错误"}`)
                      .join("；")
                  : formatUploadPackStatus(row).label
              }
            />
          ))}
        </Space>
      ) : null}

      {storedPacks.length > 0 ? (
        <div ref={metadataStepRef}>
          {storedPacks.map((row) => (
            <Card
              key={row.engagement_id}
              size="small"
              style={{ marginBottom: 10 }}
              title={
                <Space wrap size={6}>
                  <span>{row.project_name || row.engagement_id}</span>
                  {row.metadata_complete ? (
                    <Tag color="success" style={{ margin: 0 }}>
                      已完善
                    </Tag>
                  ) : (
                    <Tag color="warning" style={{ margin: 0 }}>
                      待完善
                    </Tag>
                  )}
                </Space>
              }
            >
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
            </Card>
          ))}
        </div>
      ) : null}

      {showPostUploadActions && summary && summary.stored > 0 ? (
        <Space style={{ marginTop: 4 }} wrap>
          <Tooltip
            title={
              metadataIncomplete
                ? "请先填写并保存上方项目信息"
                : "将本批项目写入检索库，供 RFQ 相似历史使用"
            }
          >
            <Button
              type="primary"
              disabled={writeProtected || metadataIncomplete}
              onClick={() => {
                setShowPostUploadActions(false);
                onRequestIndex?.();
              }}
            >
              更新检索
            </Button>
          </Tooltip>
          <Button
            onClick={() => {
              if (metadataIncomplete) {
                Modal.confirm({
                  title: "尚未完善项目信息",
                  content: "可稍后在「历史项目」中完善；未完善前无法更新检索。",
                  okText: "稍后完善",
                  cancelText: "继续填写",
                  onOk: () => setShowPostUploadActions(false),
                });
                return;
              }
              setShowPostUploadActions(false);
            }}
          >
            关闭
          </Button>
        </Space>
      ) : null}
    </>
  );

  if (variant === "plain") {
    return body;
  }
  return (
    <Card title="添加历史项目" style={{ marginBottom: 16 }} size="small">
      {body}
    </Card>
  );
}
