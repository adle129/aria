"use client";

import { InfoCircleOutlined } from "@ant-design/icons";
import { Card, Space, Table, Tag, Tooltip, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import { parseApiTimestamp } from "@/lib/apiTime";
import {
  formatEngagementIndexStatus,
  formatEngagementTier,
} from "@/lib/engagementCompleteness";

const { Text } = Typography;

interface EngagementAuditRow {
  engagement_id: string;
  project_name: string;
  tier?: string | null;
  index_status: string;
  content_hash?: string | null;
  uploaded_at?: string | null;
  last_indexed_at?: string | null;
  last_error?: string | null;
  folder_path: string;
}

function formatApiTime(value?: string | null): string {
  const ts = parseApiTimestamp(value);
  if (Number.isNaN(ts)) return "—";
  return new Date(ts).toLocaleString();
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
}

export default function EngagementInventoryPanel({
  refreshToken = 0,
}: EngagementInventoryPanelProps) {
  const [rows, setRows] = useState<EngagementAuditRow[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get<{
        code: number;
        data: { engagements: EngagementAuditRow[] };
      }>("/knowledge/engagements");
      setRows(resp.data.data.engagements ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshToken]);

  return (
    <Card
      title="历史项目资料"
      size="small"
      style={{ marginBottom: 16 }}
      extra={
        <Text type="secondary" style={{ fontSize: 12 }}>
          完整度在上传或更新索引后自动评估
        </Text>
      }
    >
      <Table
        size="small"
        rowKey="engagement_id"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
        expandable={{
          expandedRowRender: (row) => (
            <Space direction="vertical" size={4}>
              <Text type="secondary">项目目录：{row.folder_path}</Text>
              {row.content_hash ? (
                <Text type="secondary">
                  内容校验码：{row.content_hash.slice(0, 12)}…
                </Text>
              ) : null}
              {row.last_error ? (
                <Text type="danger">失败原因：{row.last_error}</Text>
              ) : null}
            </Space>
          ),
        }}
        columns={[
          { title: "项目名称", dataIndex: "project_name" },
          {
            title: (
              <ColumnTitle
                title="项目目录名"
                tip="服务器 knowledge_base 下的文件夹名，用于识别同一套历史资料。"
              />
            ),
            dataIndex: "engagement_id",
          },
          {
            title: (
              <ColumnTitle
                title="资料完整度"
                tip="按 RFQ、Q&A 清单、人力报价是否齐全划分：金级（齐全）、银级（缺报价）、铜级（缺 Q&A 或多项）。"
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
            title: "索引状态",
            dataIndex: "index_status",
            render: (status: string) => {
              const formatted = formatEngagementIndexStatus(status);
              return <Tag color={formatted.color}>{formatted.label}</Tag>;
            },
          },
          {
            title: "上传时间",
            dataIndex: "uploaded_at",
            render: formatApiTime,
          },
          {
            title: "最后索引时间",
            dataIndex: "last_indexed_at",
            render: formatApiTime,
          },
        ]}
      />
    </Card>
  );
}
