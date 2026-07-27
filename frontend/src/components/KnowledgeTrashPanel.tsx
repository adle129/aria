"use client";

import { Button, Card, Modal, Space, Table, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import { parseApiTimestamp } from "@/lib/apiTime";

const { Text } = Typography;

export type TrashItemRow = {
  trash_id: string;
  item_kind: "engagement" | "document" | string;
  engagement_id: string;
  doc_type?: string | null;
  project_name?: string | null;
  display_name?: string | null;
  deleted_at?: string | null;
  purge_after?: string | null;
  days_remaining?: number | null;
};

const DOC_TYPE_LABEL: Record<string, string> = {
  rfq: "RFQ",
  qa: "问答清单",
  quote_manpower: "人力报价",
  summary: "方案摘要",
};

function formatApiTime(value?: string | null): string {
  const ts = parseApiTimestamp(value);
  if (Number.isNaN(ts)) return "—";
  return new Date(ts).toLocaleString();
}

type Props = {
  refreshToken?: number;
  writeProtected?: boolean;
  onRestored?: () => void;
};

export default function KnowledgeTrashPanel({
  refreshToken = 0,
  writeProtected = false,
  onRestored,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<TrashItemRow[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get<{
        data: { items: TrashItemRow[] };
      }>("/knowledge/trash");
      setItems(data.data?.items || []);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg ||
        "加载回收站失败";
      message.error(detail);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshToken]);

  const restore = useCallback(
    async (row: TrashItemRow) => {
      setBusyId(row.trash_id);
      try {
        await apiClient.post(
          `/knowledge/trash/${encodeURIComponent(row.trash_id)}/restore`,
        );
        message.success("已恢复。请点击上方「更新检索」后才会用于相似项目对标。");
        onRestored?.();
        await load();
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { msg?: string } } })?.response?.data
            ?.msg || "恢复失败";
        message.error(detail);
      } finally {
        setBusyId(null);
      }
    },
    [load, onRestored],
  );

  const purge = useCallback(
    (row: TrashItemRow) => {
      Modal.confirm({
        title: "彻底删除？",
        content: "删除后不可恢复。",
        okText: "彻底删除",
        okButtonProps: { danger: true },
        cancelText: "取消",
        onOk: async () => {
          setBusyId(row.trash_id);
          try {
            await apiClient.delete(
              `/knowledge/trash/${encodeURIComponent(row.trash_id)}`,
            );
            message.success("已彻底删除");
            await load();
          } catch (err: unknown) {
            const detail =
              (err as { response?: { data?: { msg?: string } } })?.response?.data
                ?.msg || "删除失败";
            message.error(detail);
          } finally {
            setBusyId(null);
          }
        },
      });
    },
    [load],
  );

  return (
    <Card title="回收站" size="small" style={{ marginBottom: 16 }}>
      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        已删除项目或文件保留 30 天，可恢复；到期将自动清理。恢复后请「更新检索」。
      </Text>
      <Table
        rowKey="trash_id"
        size="small"
        loading={loading}
        dataSource={items}
        pagination={false}
        locale={{ emptyText: "回收站为空" }}
        columns={[
          {
            title: "类型",
            dataIndex: "item_kind",
            width: 88,
            render: (kind: string, row) =>
              kind === "document" ? (
                <Tag>{DOC_TYPE_LABEL[row.doc_type || ""] || row.doc_type || "文件"}</Tag>
              ) : (
                <Tag color="blue">项目</Tag>
              ),
          },
          {
            title: "名称",
            dataIndex: "display_name",
            render: (name: string, row) => name || row.project_name || row.engagement_id,
          },
          {
            title: "项目编号",
            dataIndex: "engagement_id",
            width: 140,
          },
          {
            title: "删除时间",
            dataIndex: "deleted_at",
            width: 168,
            render: (v: string) => formatApiTime(v),
          },
          {
            title: "剩余天数",
            dataIndex: "days_remaining",
            width: 88,
            render: (n: number | null | undefined) =>
              n == null ? "—" : `${n} 天`,
          },
          {
            title: "操作",
            key: "actions",
            width: 160,
            render: (_: unknown, row: TrashItemRow) => (
              <Space size={0}>
                <Button
                  type="link"
                  size="small"
                  disabled={writeProtected}
                  loading={busyId === row.trash_id}
                  onClick={() => void restore(row)}
                >
                  恢复
                </Button>
                <Button
                  type="link"
                  size="small"
                  danger
                  disabled={writeProtected}
                  loading={busyId === row.trash_id}
                  onClick={() => purge(row)}
                >
                  彻底删除
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}
