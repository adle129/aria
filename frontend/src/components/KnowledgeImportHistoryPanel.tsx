"use client";

import { Button, Descriptions, Drawer, Space, Table, Tag, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import { parseApiTimestamp } from "@/lib/apiTime";

const { Text } = Typography;

function formatApiTime(value?: string | null): string {
  const ts = parseApiTimestamp(value);
  if (Number.isNaN(ts)) return "—";
  return new Date(ts).toLocaleString();
}

export interface KnowledgeImportBatch {
  import_id: string;
  job_id?: string | null;
  triggered_by?: string | null;
  mode: string;
  status: string;
  new_documents?: number;
  new_chunks?: number;
  skipped?: number;
  failed_count?: number;
  failed_files?: Array<{ path: string; error: string }>;
  engagements?: Array<Record<string, unknown>>;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
}

const STATUS_COLOR: Record<string, string> = {
  queued: "default",
  running: "processing",
  completed: "success",
  failed: "error",
  cancelled: "warning",
};

interface KnowledgeImportHistoryPanelProps {
  refreshToken?: number;
}

export default function KnowledgeImportHistoryPanel({
  refreshToken = 0,
}: KnowledgeImportHistoryPanelProps) {
  const [batches, setBatches] = useState<KnowledgeImportBatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<KnowledgeImportBatch | null>(null);

  const loadBatches = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get<{
        code: number;
        data: { batches: KnowledgeImportBatch[] };
      }>("/knowledge/batches");
      setBatches(resp.data.data.batches ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBatches();
  }, [loadBatches, refreshToken]);

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Text strong>导入批次历史</Text>
        <Button size="small" onClick={() => void loadBatches()} loading={loading}>
          刷新
        </Button>
      </Space>
      <Table
        size="small"
        rowKey="import_id"
        loading={loading}
        dataSource={batches}
        pagination={{ pageSize: 5, hideOnSinglePage: true }}
        columns={[
          {
            title: "模式",
            dataIndex: "mode",
            render: (mode: string) => (mode === "full" ? "全量" : "增量"),
          },
          {
            title: "状态",
            dataIndex: "status",
            render: (status: string) => (
              <Tag color={STATUS_COLOR[status] ?? "default"}>{status}</Tag>
            ),
          },
          {
            title: "chunks",
            dataIndex: "new_chunks",
            render: (value: number | undefined) => value ?? 0,
          },
          {
            title: "失败",
            dataIndex: "failed_count",
            render: (value: number | undefined) => value ?? 0,
          },
          {
            title: "开始",
            dataIndex: "started_at",
            render: (value: string | null | undefined) => formatApiTime(value),
          },
          {
            title: "操作",
            key: "action",
            render: (_: unknown, row: KnowledgeImportBatch) => (
              <Button type="link" size="small" onClick={() => setSelected(row)}>
                详情
              </Button>
            ),
          },
        ]}
      />
      <Drawer
        title="导入批次详情"
        open={selected != null}
        onClose={() => setSelected(null)}
        width={520}
      >
        {selected ? (
          <>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="批次 ID">{selected.import_id}</Descriptions.Item>
              <Descriptions.Item label="Job ID">{selected.job_id ?? "—"}</Descriptions.Item>
              <Descriptions.Item label="模式">
                {selected.mode === "full" ? "全量重建" : "增量导入"}
              </Descriptions.Item>
              <Descriptions.Item label="状态">{selected.status}</Descriptions.Item>
              <Descriptions.Item label="新增文档">
                {selected.new_documents ?? 0}
              </Descriptions.Item>
              <Descriptions.Item label="新增 chunks">
                {selected.new_chunks ?? 0}
              </Descriptions.Item>
              <Descriptions.Item label="跳过">{selected.skipped ?? 0}</Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {formatApiTime(selected.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label="结束时间">
                {formatApiTime(selected.finished_at)}
              </Descriptions.Item>
              {selected.error_message ? (
                <Descriptions.Item label="错误">{selected.error_message}</Descriptions.Item>
              ) : null}
            </Descriptions>
            {(selected.failed_files?.length ?? 0) > 0 ? (
              <Table
                style={{ marginTop: 16 }}
                size="small"
                rowKey={(row) => `${row.path}-${row.error}`}
                pagination={false}
                dataSource={selected.failed_files}
                columns={[
                  { title: "路径", dataIndex: "path" },
                  { title: "错误", dataIndex: "error" },
                ]}
              />
            ) : null}
          </>
        ) : null}
      </Drawer>
    </>
  );
}
