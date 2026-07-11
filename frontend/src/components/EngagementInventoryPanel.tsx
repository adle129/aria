"use client";

import { Card, Space, Table, Tag, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import { parseApiTimestamp } from "@/lib/apiTime";

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

const STATUS_COLOR: Record<string, string> = {
  indexed: "success",
  pending: "default",
  failed: "error",
};

function formatApiTime(value?: string | null): string {
  const ts = parseApiTimestamp(value);
  if (Number.isNaN(ts)) return "—";
  return new Date(ts).toLocaleString();
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
    <Card title="项目清单（真实状态）" size="small" style={{ marginBottom: 16 }}>
      <Table
        size="small"
        rowKey="engagement_id"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
        expandable={{
          expandedRowRender: (row) => (
            <Space direction="vertical">
              <Text type="secondary">路径：{row.folder_path}</Text>
              <Text type="secondary">
                Hash：{row.content_hash?.slice(0, 12) ?? "—"}
              </Text>
              {row.last_error ? (
                <Text type="danger">{row.last_error}</Text>
              ) : null}
            </Space>
          ),
        }}
        columns={[
          { title: "项目", dataIndex: "project_name" },
          { title: "ID", dataIndex: "engagement_id" },
          {
            title: "Tier",
            dataIndex: "tier",
            render: (tier: string | null | undefined) => tier ?? "—",
          },
          {
            title: "索引状态",
            dataIndex: "index_status",
            render: (status: string) => (
              <Tag color={STATUS_COLOR[status] ?? "default"}>{status}</Tag>
            ),
          },
          {
            title: "上传",
            dataIndex: "uploaded_at",
            render: formatApiTime,
          },
          {
            title: "最后索引",
            dataIndex: "last_indexed_at",
            render: formatApiTime,
          },
        ]}
      />
    </Card>
  );
}
