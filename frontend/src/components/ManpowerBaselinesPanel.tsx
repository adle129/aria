"use client";

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Space,
  Table,
  Tooltip,
  Typography,
  message,
} from "antd";
import { DownloadOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/api/client";

const { Text } = Typography;

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

function sourceFileName(path?: string | null): string {
  if (!path) return "—";
  const parts = path.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || path;
}

export default function ManpowerBaselinesPanel({ engagementId }: { engagementId?: string | null }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<BaselinesResponse | null>(null);
  const singleProjectMode = Boolean(engagementId);

  const loadBaselines = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get<{ code: number; data: BaselinesResponse }>(
        "/knowledge/baselines",
      );
      setData(resp.data.data);
    } catch {
      message.error("加载人天明细失败");
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

  const focused = projects[0];

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
    <div id="manpower-baselines-engagement" style={{ scrollMarginTop: 72 }}>
      {singleProjectMode && focused ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={
            focused.project_name
              ? `当前项目：${focused.project_name}`
              : `当前项目：${focused.engagement_id}`
          }
          description={
            <Text type="secondary" style={{ fontSize: 13 }}>
              {[focused.customer, focused.year != null ? `${focused.year} 年` : null]
                .filter(Boolean)
                .join(" · ") || "历史报价人天明细"}
              {focused.source_doc
                ? ` · 来源表 ${sourceFileName(focused.source_doc)}`
                : ""}
            </Text>
          }
        />
      ) : null}

      <Text type="secondary" style={{ display: "block", marginBottom: 12, fontSize: 13 }}>
        人天来自该历史项目的报价 Excel，可与源表对照。
        <Tooltip title="系统从报价表自动汇总各工程领域与岗位人天，供 RFQ 对标参考；不参与相似文档检索。">
          <InfoCircleOutlined style={{ marginLeft: 6, color: "rgba(0,0,0,0.45)" }} />
        </Tooltip>
      </Text>

      <Space wrap style={{ marginBottom: 12 }} size={8}>
        <Button size="small" onClick={() => void loadBaselines()} loading={loading}>
          刷新
        </Button>
        {!singleProjectMode ? (
          <Tooltip title="导出原始数据文件，供运维或离线核对。">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              disabled={!projects.length}
              onClick={exportJson}
            >
              导出数据
            </Button>
          </Tooltip>
        ) : null}
        {data?.updated_at ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            最近更新 {new Date(data.updated_at).toLocaleString("zh-CN")}
          </Text>
        ) : null}
      </Space>

      {!singleProjectMode ? (
        <Card title="项目汇总" size="small" style={{ marginBottom: 16 }}>
          <Table
            rowKey="engagement_id"
            size="small"
            loading={loading}
            dataSource={projects}
            pagination={{ pageSize: 8, hideOnSinglePage: true }}
            locale={{ emptyText: "暂无人天数据；请先入库含报价 Excel 的历史项目并更新检索" }}
            columns={[
              {
                title: "项目名",
                dataIndex: "project_name",
                ellipsis: true,
                render: (name: string | undefined, row) => name || row.engagement_id,
              },
              {
                title: "工程领域数",
                width: 100,
                render: (_: unknown, row) => Object.keys(row.functions || {}).length,
              },
              {
                title: "合计人天",
                width: 100,
                render: (_: unknown, row) => sumProjectManDays(row).toFixed(1),
              },
              {
                title: "来源报价表",
                dataIndex: "source_doc",
                ellipsis: true,
                render: (v?: string) => (
                  <Tooltip title={v || undefined}>{sourceFileName(v)}</Tooltip>
                ),
              },
            ]}
            expandable={{
              expandedRowRender: (project) => (
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="客户">{project.customer || "—"}</Descriptions.Item>
                  <Descriptions.Item label="年份">{project.year ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="项目 ID">{project.engagement_id}</Descriptions.Item>
                  <Descriptions.Item label="来源路径" span={2}>
                    {project.source_doc || "—"}
                  </Descriptions.Item>
                </Descriptions>
              ),
            }}
          />
        </Card>
      ) : focused ? (
        <Card size="small" style={{ marginBottom: 16 }} loading={loading}>
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="合计人天">
              <Text strong>{sumProjectManDays(focused).toFixed(1)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="工程领域数">
              {Object.keys(focused.functions || {}).length}
            </Descriptions.Item>
            <Descriptions.Item label="来源报价表" span={2}>
              <Tooltip title={focused.source_doc || undefined}>
                {sourceFileName(focused.source_doc)}
              </Tooltip>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      ) : (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="未找到该项目的人天数据"
          description="可能尚未解析报价 Excel，或入库后未更新检索。"
        />
      )}

      <Card title="按工程领域" size="small">
        <Table
          rowKey="key"
          size="small"
          loading={loading}
          dataSource={functionRows}
          pagination={{ pageSize: 12, hideOnSinglePage: true }}
          locale={{ emptyText: "暂无按工程领域汇总的人天" }}
          columns={[
            ...(singleProjectMode
              ? []
              : [
                  {
                    title: "项目",
                    dataIndex: "project_name",
                    width: 140,
                    ellipsis: true,
                  },
                ]),
            { title: "工程领域", dataIndex: "function", width: 120 },
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
                locale={{ emptyText: "无岗位明细" }}
                columns={[
                  { title: "岗位", dataIndex: "position", ellipsis: true },
                  {
                    title: (
                      <Tooltip title="报价 Excel 中的工作表名称">
                        <span>工作表</span>
                      </Tooltip>
                    ),
                    dataIndex: "sheet",
                    width: 110,
                    ellipsis: true,
                  },
                  {
                    title: (
                      <Tooltip title="源表中的行号，便于对照 Excel">
                        <span>表行号</span>
                      </Tooltip>
                    ),
                    dataIndex: "excel_row",
                    width: 72,
                  },
                  {
                    title: "人天",
                    dataIndex: "sum",
                    width: 80,
                  },
                ]}
              />
            ),
          }}
        />
      </Card>
    </div>
  );
}
