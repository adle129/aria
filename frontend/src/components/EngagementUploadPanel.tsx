"use client";

import { InboxOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Input, Space, Table, Tag, Typography, Upload, message } from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import { useMemo, useState } from "react";
import { apiClient } from "@/api/client";
import { uploadNeedsEngagementId } from "@/lib/engagementUpload";

const { Paragraph, Text } = Typography;

export interface EngagementPackResult {
  engagement_id: string;
  project_name?: string;
  status: string;
  stored: boolean;
  tier: "gold" | "silver" | "copper";
  indexable: boolean;
  missing?: string[];
  automation_impacts: string[];
  path?: string;
  files?: string[];
  errors?: Array<{ file?: string; error?: string }>;
}

const TIER_COLOR: Record<string, string> = {
  gold: "green",
  silver: "blue",
  copper: "orange",
};

const TIER_LABEL: Record<EngagementPackResult["tier"], string> = {
  gold: "金级",
  silver: "银级",
  copper: "铜级",
};

const MISSING_LABEL: Record<string, string> = {
  rfq: "RFQ",
  qa: "Q&A",
  quote_manpower: "人力报价 Excel",
};

interface EngagementUploadPanelProps {
  onUploaded?: () => void;
}

export default function EngagementUploadPanel({ onUploaded }: EngagementUploadPanelProps) {
  const [engagementId, setEngagementId] = useState("");
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [lastResults, setLastResults] = useState<EngagementPackResult[] | null>(null);

  const fileNames = useMemo(() => fileList.map((f) => f.name), [fileList]);
  const needsEngagementId = uploadNeedsEngagementId(fileNames);
  const zipCount = fileNames.filter((n) => n.toLowerCase().endsWith(".zip")).length;

  const handleUpload = async () => {
    if (!fileList.length) {
      message.warning("请选择 ZIP 或项目文件");
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

    const form = new FormData();
    for (const f of fileList) {
      if (f.originFileObj) {
        form.append("files", f.originFileObj, f.name);
      }
    }
    if (needsEngagementId) {
      form.append("engagement_id", engagementId.trim());
    }

    setUploading(true);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: { packs: EngagementPackResult[]; uploaded: number };
      }>("/knowledge/engagements/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setLastResults(resp.data.data.packs);
      const failed = resp.data.data.packs.filter((p) => !p.stored).length;
      const incomplete = resp.data.data.packs.filter((p) => p.missing?.length).length;
      if (failed > 0) {
        message.warning(
          `已处理 ${resp.data.data.uploaded} 套，其中 ${failed} 套上传失败；请查看下表`,
        );
      } else if (incomplete > 0) {
        message.info(
          `已上传 ${resp.data.data.uploaded} 套，其中 ${incomplete} 套资料不完整；可索引项目请查看下表`,
        );
      } else {
        message.success(`已上传 ${resp.data.data.uploaded} 套，请点击「更新知识库索引」`);
      }
      setFileList([]);
      onUploaded?.();
    } catch {
      // apiClient interceptor
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card title="上传项目包" style={{ marginBottom: 16 }} size="small">
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        单套：上传 <Text strong>ZIP</Text>（推荐，目录内含 RFQ / Q_A / 报价 Excel），或填写{" "}
        <Text strong>Engagement ID</Text> 后一次选择多文件。单次最多 <Text strong>5</Text> 个
        ZIP；散文件模式每次 1 套。
      </Paragraph>

      {needsEngagementId && (
        <Space style={{ marginBottom: 12 }} wrap>
          <Text>Engagement ID：</Text>
          <Input
            style={{ width: 280 }}
            placeholder="如 dev_chassis_2024"
            value={engagementId}
            onChange={(e) => setEngagementId(e.target.value)}
          />
        </Space>
      )}

      <Upload.Dragger
        multiple
        fileList={fileList}
        beforeUpload={() => false}
        onChange={({ fileList: next }) => setFileList(next)}
        accept=".zip,.docx,.doc,.xlsx,.json"
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽 ZIP / RFQ / Q_A / 报价 Excel / manifest.json</p>
        <p className="ant-upload-hint">ZIP 无需填 ID；散文件须先填 Engagement ID</p>
      </Upload.Dragger>

      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          loading={uploading}
          disabled={!fileList.length}
          onClick={() => void handleUpload()}
        >
          上传并落盘
        </Button>
        <Button onClick={() => setFileList([])} disabled={!fileList.length || uploading}>
          清空选择
        </Button>
      </Space>

      {lastResults && lastResults.length > 0 && (
        <Table
          style={{ marginTop: 16 }}
          rowKey="engagement_id"
          size="small"
          pagination={false}
          scroll={{ x: "max-content" }}
          dataSource={lastResults}
          columns={[
            { title: "Engagement", dataIndex: "engagement_id", width: 160 },
            { title: "项目名", dataIndex: "project_name", ellipsis: true },
            {
              title: "等级",
              key: "tier",
              width: 72,
              render: (_: unknown, row: EngagementPackResult) => (
                <Tag color={TIER_COLOR[row.tier]}>{TIER_LABEL[row.tier]}</Tag>
              ),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 136,
              render: (_: string, row: EngagementPackResult) => (
                <Tag color={row.indexable ? "green" : "red"}>
                  {row.indexable ? "已上传·可索引" : "已上传·不可索引"}
                </Tag>
              ),
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
                  : "三件套齐全，可支撑 R1 检索与后续里程碑",
            },
            { title: "路径", dataIndex: "path", ellipsis: true },
          ]}
        />
      )}

      <Alert
        type="info"
        showIcon
        style={{ marginTop: 16 }}
        message="上传后须点击「更新知识库索引」方可检索"
      />
    </Card>
  );
}
