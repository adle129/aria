"use client";

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Space,
  Table,
  Typography,
  message,
} from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/api/client";

const { Paragraph, Text } = Typography;

interface BaselinePosition {
  position: string;
  sheet?: string;
  excel_row?: number;
  sum?: number | string;
}

interface BaselineFunction {
  total_man_days?: number;
  positions?: BaselinePosition[];
}

interface BaselineProject {
  engagement_id: string;
  project_name?: string;
  customer?: string;
  year?: number;
  source_doc?: string;
  functions?: Record<string, BaselineFunction>;
}

interface BaselinesResponse {
  updated_at?: string | null;
  import_batch_id?: string | null;
  projects: BaselineProject[];
}

function sumProjectManDays(project: BaselineProject): number {
  const fns = project.functions || {};
  return Object.values(fns).reduce((acc, fn) => acc + Number(fn.total_man_days || 0), 0);
}

export default function ManpowerBaselinesPanel({ engagementId }: { engagementId?: string | null }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<BaselinesResponse | null>(null);

  const loadBaselines = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get<{ code: number; data: BaselinesResponse }>(
        "/knowledge/baselines",
      );
      setData(resp.data.data);
    } catch {
      message.error("加载人天基线失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBaselines();
  }, [loadBaselines]);

  const exportJson = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `manpower_baselines_${data.import_batch_id || "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const projects = useMemo(() => {
    const all = data?.projects || [];
    if (!engagementId) return all;
    return all.filter((p) => p.engagement_id === engagementId);
  }, [data?.projects, engagementId]);

  const functionRows = useMemo(() => {
    const rows: Array<{
      key: string;
      engagement_id: string;
      project_name: string;
      function: string;
      total_man_days: number;
      position_count: number;
      source_doc?: string;
      positions: BaselinePosition[];
    }> = [];
    for (const project of projects) {
      for (const [fn, detail] of Object.entries(project.functions || {})) {
        rows.push({
          key: `${project.engagement_id}::${fn}`,
          engagement_id: project.engagement_id,
          project_name: project.project_name || project.engagement_id,
          function: fn,
          total_man_days: Number(detail.total_man_days || 0),
          position_count: (detail.positions || []).length,
          source_doc: project.source_doc,
          positions: detail.positions || [],
        });
      }
    }
    return rows;
  }, [projects]);

  useEffect(() => {
    if (!engagementId || loading) return;
    const timer = window.setTimeout(() => {
      document
        .getElementById("manpower-baselines-engagement")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
    return () => window.clearTimeout(timer);
  }, [engagementId, loading, projects.length]);

  return (
    <div>
      {engagementId && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={`已筛选 Engagement：${engagementId}`}
        />
      )}
      <Paragraph type="secondary">
        历史报价 Excel 经规则解析写入 <Text code>manpower_baselines.json</Text>，不进向量索引。可与源
        Excel 对照验收各 Function 人天。
      </Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 12 }}>
          <Button onClick={() => void loadBaselines()} loading={loading}>
            刷新基线
          </Button>
          <Button icon={<DownloadOutlined />} disabled={!projects.length} onClick={exportJson}>
            导出 JSON
          </Button>
        </Space>
        {data?.updated_at && (
          <Text type="secondary" style={{ display: "block" }}>
            最近更新：{new Date(data.updated_at).toLocaleString("zh-CN")}
            {data.import_batch_id ? ` · 批次 ${data.import_batch_id}` : null}
          </Text>
        )}
      </Card>

      <Card
        id="manpower-baselines-engagement"
        title="Engagement 汇总"
        style={{ marginBottom: 16, scrollMarginTop: 72 }}
      >
        <Table
          rowKey="engagement_id"
          size="small"
          loading={loading}
          dataSource={projects}
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          locale={{ emptyText: "暂无基线数据；请先导入含报价 Excel 的 Engagement 并更新索引" }}
          columns={[
            { title: "Engagement", dataIndex: "engagement_id", width: 160 },
            { title: "项目名", dataIndex: "project_name", ellipsis: true },
            {
              title: "Function 数",
              width: 100,
              render: (_, row) => Object.keys(row.functions || {}).length,
            },
            {
              title: "合计人天",
              width: 100,
              render: (_, row) => sumProjectManDays(row).toFixed(1),
            },
            { title: "源 Excel", dataIndex: "source_doc", ellipsis: true },
          ]}
          expandable={{
            expandedRowRender: (project) => (
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="客户">{project.customer || "—"}</Descriptions.Item>
                <Descriptions.Item label="年份">{project.year ?? "—"}</Descriptions.Item>
                <Descriptions.Item label="源文档" span={2}>
                  {project.source_doc || "—"}
                </Descriptions.Item>
              </Descriptions>
            ),
          }}
        />
      </Card>

      <Card title="Function 人天钻取">
        <Table
          rowKey="key"
          size="small"
          loading={loading}
          dataSource={functionRows}
          pagination={{ pageSize: 12, hideOnSinglePage: true }}
          locale={{ emptyText: "无 Function 级基线" }}
          columns={[
            { title: "Engagement", dataIndex: "engagement_id", width: 140, ellipsis: true },
            { title: "Function", dataIndex: "function", width: 100 },
            {
              title: "合计人天",
              dataIndex: "total_man_days",
              width: 100,
              render: (v: number) => v.toFixed(1),
            },
            {
              title: "岗位数",
              dataIndex: "position_count",
              width: 80,
            },
          ]}
          expandable={{
            expandedRowRender: (row) => (
              <Table
                size="small"
                rowKey={(p, i) => `${row.key}-${i}`}
                pagination={false}
                dataSource={row.positions}
                columns={[
                  { title: "岗位", dataIndex: "position", ellipsis: true },
                  { title: "Sheet", dataIndex: "sheet", width: 100 },
                  { title: "行", dataIndex: "excel_row", width: 60 },
                  { title: "Sum", dataIndex: "sum", width: 80 },
                ]}
              />
            ),
          }}
        />
      </Card>
    </div>
  );
}
